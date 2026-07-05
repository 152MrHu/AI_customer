"""统一日志配置"""
import logging
import sys
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from common.config import settings

_logger: logging.Logger = None


def setup_logger(name: str = "app") -> logging.Logger:
    global _logger
    if _logger:
        return _logger

    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    # 控制台
    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    logger.addHandler(console)

    # 文件（按天滚动，保留 30 天）
    # 每个服务单独一个日志文件，避免多进程共用同一文件导致 Windows 文件锁冲突
    file_handler = TimedRotatingFileHandler(
        log_dir / f"{name}.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))
    logger.addHandler(file_handler)

    _logger = logger
    return logger


def get_logger() -> logging.Logger:
    if _logger:
        return _logger
    return setup_logger()
