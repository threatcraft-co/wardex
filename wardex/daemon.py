"""FSEvents-based daemon that watches the VS Code extensions directory."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from wardex.marketplace import MarketplaceClient, MarketplaceError
from wardex.policy import Decision, evaluate
from wardex.quarantine import quarantine

logger = logging.getLogger(__name__)

DEFAULT_EXTENSIONS_DIR = Path("~/.vscode/extensions").expanduser()
DEFAULT_QUARANTINE_DIR = Path("~/.wardex/quarantine").expanduser()
PACKAGE_JSON_WAIT_SECONDS = 5.0
PACKAGE_JSON_POLL_INTERVAL = 0.2


class ExtensionInstallHandler(FileSystemEventHandler):
    """Reacts to new extension directories appearing under the extensions root.

    VS Code creates an extension directory by extracting a .vsix archive, which
    on macOS often coalesces filesystem events such that `on_created` for the
    parent directory may not fire reliably. Instead we listen for any event in
    the watched tree and, on each event, scan the extensions root for new
    subdirectories we have not seen before.
    """

    def __init__(
        self,
        extensions_root: Path,
        marketplace: MarketplaceClient,
        allowlist_publishers: list[str],
        allowlist_extensions: list[str],
        blocklist_extensions: set[str],
        quarantine_dir: Path,
        enforce: bool,
        api_failure_policy: str,
    ):
        super().__init__()
        self.extensions_root = extensions_root
        self.marketplace = marketplace
        self.allowlist_publishers = allowlist_publishers
        self.allowlist_extensions = allowlist_extensions
        self.blocklist_extensions = blocklist_extensions
        self.quarantine_dir = quarantine_dir
        self.enforce = enforce
        self.api_failure_policy = api_failure_policy
        # Snapshot of extension dirs we've already evaluated
        self._seen: set[str] = set()
        # Debounce: skip scans more than once per interval
        self._last_scan_time: float = 0.0
        self._scan_debounce_seconds: float = 0.5

    def baseline(self) -> None:
        """Record currently installed extensions without evaluating them."""
        for entry in self._list_extension_dirs():
            self._seen.add(entry.name)
        logger.info("Baseline: %d existing extensions recorded", len(self._seen))

    def _list_extension_dirs(self) -> list[Path]:
        """Return immediate subdirectories of the extensions root."""
        if not self.extensions_root.exists():
            return []
        return [
            p
            for p in self.extensions_root.iterdir()
            if p.is_dir() and not p.name.startswith(".") and p.name != "node_modules"
        ]

    def on_any_event(self, event):
        """Trigger a scan on relevant filesystem events in the extensions root."""
        # A rename/move carries the destination in dest_path; both endpoints matter
        candidate_paths = [event.src_path]
        if getattr(event, "dest_path", None):
            candidate_paths.append(event.dest_path)

        # Determine whether this event touches the top level of extensions_root
        relevant = False
        force_scan = False
        for raw_path in candidate_paths:
            try:
                event_path = Path(raw_path)
                relative = event_path.relative_to(self.extensions_root)
            except (ValueError, OSError):
                continue

            # Top-level events only
            if len(relative.parts) != 1:
                continue

            relevant = True

            # Directory creates and moves at the top level are the signals we
            # most care about — never let debouncing hide them.
            if event.is_directory and event.event_type in ("created", "moved"):
                force_scan = True

        if not relevant:
            return

        logger.debug(
            "FSEvent: type=%s is_dir=%s src=%s dest=%s force=%s",
            event.event_type,
            event.is_directory,
            event.src_path,
            getattr(event, "dest_path", ""),
            force_scan,
        )

        self._scan_for_new_extensions(force=force_scan)

    def _scan_for_new_extensions(self, force: bool = False) -> None:
        """Find extension directories that have appeared since last check."""
        now = time.time()
        if not force and now - self._last_scan_time < self._scan_debounce_seconds:
            return
        self._last_scan_time = now

        for ext_dir in self._list_extension_dirs():
            if ext_dir.name in self._seen:
                continue
            self._seen.add(ext_dir.name)
            logger.info("New extension directory detected: %s", ext_dir.name)
            self._process_extension(ext_dir)

    def _process_extension(self, path: Path) -> None:
        """Read package.json, query Marketplace, evaluate policy, act."""
        manifest = self._wait_for_package_json(path)
        if manifest is None:
            logger.error("Could not read package.json in %s — skipping", path.name)
            return

        publisher = manifest.get("publisher")
        name = manifest.get("name")
        if not publisher or not name:
            logger.error("package.json missing publisher or name: %s", path.name)
            return

        extension_id = f"{publisher}.{name}"
        logger.info("Checking extension: %s", extension_id)

        try:
            info = self.marketplace.fetch_extension(extension_id)
        except MarketplaceError as e:
            self._handle_api_failure(path, extension_id, str(e))
            return

        result = evaluate(
            info,
            self.allowlist_publishers,
            self.allowlist_extensions,
            self.blocklist_extensions,
        )

        logger.info(
            "Policy decision for %s: %s (%s)",
            extension_id,
            result.decision.value,
            result.reason,
        )

        if result.decision == Decision.BLOCK:
            self._handle_block(path, extension_id, result.reason)
        elif result.decision == Decision.FLAG:
            self._handle_flag(path, extension_id, result.reason)
        else:
            self._handle_allow(extension_id, result.reason)

    def _wait_for_package_json(self, ext_dir: Path) -> Optional[dict]:
        """Wait for VS Code to finish writing package.json, then read it."""
        package_json = ext_dir / "package.json"
        deadline = time.time() + PACKAGE_JSON_WAIT_SECONDS

        while time.time() < deadline:
            if package_json.exists():
                try:
                    with package_json.open("r", encoding="utf-8") as f:
                        return json.load(f)
                except (json.JSONDecodeError, OSError):
                    time.sleep(PACKAGE_JSON_POLL_INTERVAL)
                    continue
            time.sleep(PACKAGE_JSON_POLL_INTERVAL)

        return None

    def _handle_block(self, path: Path, extension_id: str, reason: str) -> None:
        if self.enforce:
            try:
                target = quarantine(path, self.quarantine_dir)
                logger.warning(
                    "BLOCKED %s — %s — quarantined to %s",
                    extension_id,
                    reason,
                    target,
                )
            except Exception as e:
                logger.error("Failed to quarantine %s: %s", extension_id, e)
        else:
            logger.warning(
                "WOULD BLOCK %s — %s (alert mode; extension left in place)",
                extension_id,
                reason,
            )

    def _handle_flag(self, path: Path, extension_id: str, reason: str) -> None:
        logger.warning("FLAGGED %s — %s", extension_id, reason)

    def _handle_allow(self, extension_id: str, reason: str) -> None:
        logger.info("ALLOWED %s — %s", extension_id, reason)

    def _handle_api_failure(self, path: Path, extension_id: str, error: str) -> None:
        logger.error("Marketplace API failure for %s: %s", extension_id, error)
        if self.api_failure_policy == "fail_closed":
            self._handle_block(path, extension_id, f"API unreachable (fail_closed): {error}")
        else:
            logger.warning(
                "Allowing %s due to fail_open policy despite API failure",
                extension_id,
            )


def run(
    extensions_dir: Path = DEFAULT_EXTENSIONS_DIR,
    quarantine_dir: Path = DEFAULT_QUARANTINE_DIR,
    enforce: bool = False,
    api_failure_policy: str = "fail_closed",
    allowlist_publishers: Optional[list[str]] = None,
    allowlist_extensions: Optional[list[str]] = None,
    blocklist_extensions: Optional[set[str]] = None,
) -> None:
    """Start the FSEvents observer and block."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if not extensions_dir.exists():
        logger.warning("Extensions directory does not exist yet: %s", extensions_dir)
        extensions_dir.mkdir(parents=True, exist_ok=True)

    marketplace = MarketplaceClient()
    handler = ExtensionInstallHandler(
        extensions_root=extensions_dir,
        marketplace=marketplace,
        allowlist_publishers=allowlist_publishers or [],
        allowlist_extensions=allowlist_extensions or [],
        blocklist_extensions=blocklist_extensions or set(),
        quarantine_dir=quarantine_dir,
        enforce=enforce,
        api_failure_policy=api_failure_policy,
    )

    # Baseline: don't evaluate extensions that were already there
    handler.baseline()

    observer = Observer()
    # recursive=True so we catch events inside newly extracted extension dirs
    observer.schedule(handler, str(extensions_dir), recursive=True)
    observer.start()

    mode = "ENFORCE" if enforce else "ALERT"
    logger.info("Wardex started in %s mode — watching %s", mode, extensions_dir)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Stopping wardex...")
        observer.stop()
    observer.join()