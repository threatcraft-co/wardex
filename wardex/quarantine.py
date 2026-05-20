"""Safely remove or move blocked extensions out of the VS Code extensions dir."""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def quarantine(extension_dir: Path, quarantine_root: Path) -> Path:
    """Move a blocked extension directory into the quarantine area.

    Returns the new path so it can be referenced in alerts.
    """
    quarantine_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    target = quarantine_root / f"{extension_dir.name}__{timestamp}"
    shutil.move(str(extension_dir), str(target))
    logger.warning("Quarantined extension: %s -> %s", extension_dir, target)
    return target