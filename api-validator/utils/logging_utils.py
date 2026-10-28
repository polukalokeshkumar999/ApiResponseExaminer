from __future__ import annotations

import logging
from pathlib import Path

from utils.io_utils import ensure_dir


def configure_logging(log_path: Path) -> None:
    ensure_dir(log_path.parent)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
