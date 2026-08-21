"""
agent2win — Logging & Audit Trail
"""
import logging
import json
import time
from pathlib import Path
from .config import Settings

def setup_logger(settings: Settings) -> logging.Logger:
    log_path = Path(settings.log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("agent2win")
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    fmt = logging.Formatter("\033[90m[%(asctime)s]\033[0m \033[94m%(levelname)s\033[0m | %(message)s", datefmt="%H:%M:%S")
    file_fmt = logging.Formatter("[%(asctime)s] %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    fh = logging.FileHandler(log_path, encoding="utf-8")
    fh.setFormatter(file_fmt)
    logger.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setFormatter(fmt)
    logger.addHandler(ch)

    return logger

def audit_log(settings: Settings, action: str, details: dict, approved: bool = True):
    """Append a JSON line to the audit log for every agent action."""
    audit_path = Path(settings.audit_log)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": time.time(),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "action": action,
        "approved": approved,
        **details,
    }
    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
