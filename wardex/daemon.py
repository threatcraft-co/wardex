"""FSEvents-based daemon that watches the VS Code extensions directory."""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

DEFAULT_EXTENSIONS_DIR = Path("~/.vscode/extensions").expanduser()


class ExtensionInstallHandler(FileSystemEventHandler):
    """Reacts to new directories appearing in the extensions folder."""

    def on_created(self, event):
        if not event.is_directory:
            return
        path = Path(event.src_path)
        # Skip the extensions index file and obvious non-extension dirs
        if path.name.startswith(".") or path.name == "node_modules":
            return
        logger.info("New extension directory detected: %s", path)
        # TODO: parse package.json, query Marketplace, evaluate policy, act
        # This is the integration point for marketplace.py + policy.py + quarantine.py


def run(extensions_dir: Path = DEFAULT_EXTENSIONS_DIR) -> None:
    """Start the FSEvents observer and block."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if not extensions_dir.exists():
        logger.warning("Extensions directory does not exist yet: %s", extensions_dir)
        extensions_dir.mkdir(parents=True, exist_ok=True)

    handler = ExtensionInstallHandler()
    observer = Observer()
    observer.schedule(handler, str(extensions_dir), recursive=False)
    observer.start()
    logger.info("Wardex watching: %s", extensions_dir)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping wardex...")
        observer.stop()
    observer.join()