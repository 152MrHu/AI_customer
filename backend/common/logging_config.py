"""统一日志配置"""
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from common.config import settings


class SafeRotatingFileHandler(TimedRotatingFileHandler):
    """安全的日志轮转处理器：轮转失败时降级处理，不中断服务"""

    def doRollover(self):
        try:
            super().doRollover()
        except PermissionError:
            # Windows 上多进程共享日志文件时，rename 会失败
            # 降级：不清空旧文件，继续追加写入
            pass


def setup_logger(name: str = "app") -> logging.Logger:
    """创建独立的 logger，每个服务使用自己的日志文件"""

    # 先检查是否已经有同名 logger 被配置过
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger.setLevel(logging.INFO)

    # 控制台
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    logger.addHandler(console)

    # 文件（按天滚动，保留 30 天）
    # delay=True: 延迟打开文件，减少多进程文件锁冲突
    file_handler = SafeRotatingFileHandler(
        log_dir / f"{name}.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
        delay=True,
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    logger.addHandler(file_handler)

    return logger


def get_logger() -> logging.Logger:
    """获取默认 logger（不依赖全局单例）"""
    return setup_logger()
