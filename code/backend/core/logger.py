"""
DeltaForge Structured Logger
Configures rotating file handler + rich console handler.
Call setup_logging() once at startup from main.py.
"""

import logging
import logging.handlers
import os
import sys

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "deltaforge.log")
MAX_BYTES = 10 * 1024 * 1024  # 10 MB
BACKUP_COUNT = 5

_FMT_DETAILED = "%(asctime)s [%(name)-28s] %(levelname)-8s %(message)s"
_FMT_SIMPLE = "%(levelname)-8s %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"

LEVEL_MAP = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}


def setup_logging(
    level: str = "info",
    log_dir: str = LOG_DIR,
    enable_console: bool = True,
    enable_file: bool = True,
    enable_rich: bool = True,
) -> logging.Logger:
    """
    Configure root logger with:
    - RotatingFileHandler  → logs/deltaforge.log
    - StreamHandler        → stderr (with Rich if available)
    Returns the root DeltaForge logger.
    """
    lvl = LEVEL_MAP.get(level.lower(), logging.INFO)

    # Silence noisy libs
    for noisy in ("ccxt", "urllib3", "asyncio", "websockets", "requests"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    root = logging.getLogger("DeltaForge")
    root.setLevel(lvl)
    root.handlers.clear()
    root.propagate = False

    if enable_file:
        os.makedirs(log_dir, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            os.path.join(log_dir, "deltaforge.log"),
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
        fh.setLevel(lvl)
        fh.setFormatter(logging.Formatter(_FMT_DETAILED, datefmt=_DATE_FMT))
        root.addHandler(fh)

    if enable_console:
        if enable_rich:
            try:
                from rich.logging import RichHandler

                rh = RichHandler(
                    rich_tracebacks=True,
                    show_time=True,
                    show_path=False,
                    markup=True,
                )
                rh.setLevel(lvl)
                root.addHandler(rh)
            except ImportError:
                _add_stream_handler(root, lvl)
        else:
            _add_stream_handler(root, lvl)

    return root


def _add_stream_handler(logger: logging.Logger, level: int) -> None:
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(level)
    sh.setFormatter(logging.Formatter(_FMT_SIMPLE))
    logger.addHandler(sh)


def get_logger(name: str) -> logging.Logger:
    """Return a DeltaForge sub-logger. Always call this instead of logging.getLogger."""
    return logging.getLogger(f"DeltaForge.{name}")
