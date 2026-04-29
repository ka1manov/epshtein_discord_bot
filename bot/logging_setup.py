import logging
import os
from typing import Optional


def configure(level: Optional[str] = None) -> None:
    """Configure stdlib logging once.

    If `level` is provided, use it. Otherwise read LOG_LEVEL from os.environ
    (defaulting to "INFO"). Either way, the value is upper-cased and resolved
    via getattr; unknown levels fall back to INFO.

    Idempotent: calling more than once is a no-op because logging.basicConfig
    skips reconfiguration when the root logger already has handlers."""
    level_name = (level or os.environ.get("LOG_LEVEL", "INFO")).upper()
    resolved = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=resolved,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
