"""网关中间件 - 纯 ASGI 实现（保证 SSE 流式响应不被缓冲）

中间件执行顺序（注册顺序 = 洋葱层次，先注册为外层）：
    请求 -> RequestLogMiddleware -> JWTAuthMiddleware -> RateLimitMiddleware -> 路由
    响应 <- RequestLogMiddleware <- JWTAuthMiddleware <- RateLimitMiddleware <- 路由
"""
import json
import time
import uuid

from common.config import settings
from common.jwt_utils import decode_token
from common.redis_client import is_blacklisted, incr_rate_limit, get_redis
from common.response import error_response, ErrorCode
from common.logging_config import setup_logger
from common.http_client import set_request_id

from gateway.routes import is_public, is_rate_limited

logger = setup_logger("gateway")


def _inject_headers(scope: dict, extra: list[tuple[str, str]]):
	"""向 ASGI scope 注入额外的请求头（覆盖同名旧头）"""
	raw = list(scope.get("headers", []))
	names_lower = {name.lower() for name, _ in extra}
	raw = [(k, v) for k, v in raw if k.decode().lower() not in names_lower]
	for name, value in extra:
		raw.append((name.lower().encode(), str(value).encode()))
	scope["headers"] = raw


async def _send_json(send, status_code: int, payload: dict):
	"""直接通过 ASGI send 发送 JSON 响应（不经过下游应用）"""
	body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
	await send({
		"type": "http.response.start",
		"status": status_code,
		"headers": [
			(b"content-type", b"application/json; charset=utf-8"),
			(b"content-length", str(len(body)).encode()),
			(b"cache-control", b"no-cache"),
		],
	})
	await send({
		"type": "http.response.body",
		"body": body,
		"more_body": False,
	})


class RequestLogMiddleware:
	"""请求日志中间件（最外层）：记录方法/路径/状态码/耗时/请求ID"""

	def __init__(self, app):
		self.app = app

	async def __call__(self, scope, receive, send):
		if scope.get("type") != "http":
			await self.app(scope, receive, send)
			return

		method = scope.get("method", "")
		path = scope.get("path", "")

		# 提取或生成 X-Request-Id
		headers = scope.get("headers", [])
		request_id = None
		for k, v in headers:
			if k.decode().lower() == "x-request-id":
				request_id = v.decode()
				break
		if not request_id:
			request_id = str(uuid.uuid4())

		# 注入 X-Request-Id 到请求头（透传给下游服务）
		_inject_headers(scope, [("X-Request-Id", request_id)])

		# 设置到 contextvars，供下游服务间调用时转发
		set_request_id(request_id)

		start = time.time()
		status_code = 0

		async def send_wrapper(message):
			nonlocal status_code
			if message["type"] == "http.response.start":
				status_code = message["status"]
			await send(message)

		try:
			await self.app(scope, receive, send_wrapper)
		finally:
			duration = (time.time() - start) * 1000
			logger.info(
				"[%s] %s %s -> %s (%.2fms)",
				request_id, method, path, status_code, duration,
			)


class JWTAuthMiddleware:
	"""
	JWT 鉴权中间件（中间层）：
	- 公开接口放行
	- 其余校验 Authorization -> 解码 JWT -> 检查黑名单
	- 成功后注入 X-User-Id / X-User-Role 到请求头
	- 失败返回 401 JSON
	"""

	def __init__(self, app):
		self.app = app

	async def __call__(self, scope, receive, send):
		if scope.get("type") != "http":
			await self.app(scope, receive, send)
			return

		path = scope.get("path", "")

		# 公开接口放行
		if is_public(path):
			await self.app(scope, receive, send)
			return

		# 提取 Authorization 头
		headers = scope.get("headers", [])
		auth_header = None
		for k, v in headers:
			if k.decode().lower() == "authorization":
				auth_header = v.decode()
				break

		if not auth_header or not auth_header.startswith("Bearer "):
			await _send_json(
				send, 401, error_response(ErrorCode.UNAUTHORIZED, "缺少有效的认证信息")
			)
			return

		token = auth_header[len("Bearer "):].strip()
		payload = decode_token(token)
		if not payload:
			await _send_json(
				send, 401, error_response(ErrorCode.UNAUTHORIZED, "Token 无效或已过期")
			)
			return

		# 检查黑名单
		if await is_blacklisted(token):
			await _send_json(
				send, 401, error_response(ErrorCode.UNAUTHORIZED, "Token 已失效，请重新登录")
			)
			return

		# 注入用户信息到请求头（透传给下游服务）
		user_id = payload.get("user_id")
		role = payload.get("role", "user")
		if user_id is None:
			await _send_json(
				send, 401, error_response(ErrorCode.UNAUTHORIZED, "Token 缺少用户信息")
			)
			return

		_inject_headers(scope, [
			("X-User-Id", str(user_id)),
			("X-User-Role", str(role)),
		])

		await self.app(scope, receive, send)


def _get_client_ip(scope: dict) -> str:
	"""从 ASGI scope 提取客户端 IP（优先 X-Forwarded-For）"""
	headers = scope.get("headers", [])
	for k, v in headers:
		if k.decode().lower() == "x-forwarded-for":
			return v.decode().split(",")[0].strip()
	# fallback: scope 中的 client 地址
	client = scope.get("client")
	if client:
		return client[0]
	return "unknown"


class RateLimitMiddleware:
	"""
	限流中间件（最内层）：
	- 对 is_rate_limited() 返回 True 的接口限流
	- 已登录用户按 user_id 限流，公开接口按 IP 限流
	- Redis rate_limit:{user_id 或 ip} INCR，TTL 60s
	- 超过上限返回 429
	"""

	def __init__(self, app):
		self.app = app

	async def __call__(self, scope, receive, send):
		if scope.get("type") != "http":
			await self.app(scope, receive, send)
			return

		method = scope.get("method", "")
		path = scope.get("path", "")

		if not is_rate_limited(path, method):
			await self.app(scope, receive, send)
			return

		# 优先从请求头获取 X-User-Id（已登录用户），否则用 IP
		headers = scope.get("headers", [])
		rate_key = None
		for k, v in headers:
			if k.decode().lower() == "x-user-id":
				rate_key = v.decode()
				break

		if not rate_key:
			# 公开接口（登录/注册）：使用 IP 限流
			rate_key = _get_client_ip(scope)

		# 限流计数
		try:
			# 需要修改 incr_rate_limit 接受字符串 key
			count = await _incr_rate_limit_str(rate_key)
		except Exception as e:
			logger.warning("限流计数失败(放行): key=%s, err=%s", rate_key, e)
			await self.app(scope, receive, send)
			return

		limit = settings.RATE_LIMIT_PER_MIN
		# 公开接口使用更严格的限制
		public_paths = {"/api/user/login", "/api/user/register"}
		if path in public_paths:
			limit = 20  # 登录/注册：每分钟 20 次/ip

		if count > limit:
			logger.warning(
				"触发限流: key=%s, count=%s, limit=%s, path=%s",
				rate_key, count, limit, path,
			)
			await _send_json(
				send, 429,
				error_response(
					ErrorCode.RATE_LIMITED,
					f"请求过于频繁，请稍后再试",
				),
			)
			return

		await self.app(scope, receive, send)


async def _incr_rate_limit_str(key: str) -> int:
	"""递增限流计数（支持字符串 key，同时兼容 int user_id）"""
	r = get_redis()
	redis_key = f"rate_limit:{key}"
	count = await r.incr(redis_key)
	if count == 1:
		await r.expire(redis_key, 60)  # 1 分钟
	return count
