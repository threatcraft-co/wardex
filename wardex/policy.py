"""Policy evaluation.

Given an ExtensionInfo and the current configuration, decide whether to allow,
block, or flag the extension.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from wardex.marketplace import ExtensionInfo


class Decision(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    FLAG = "flag"


@dataclass
class PolicyResult:
    decision: Decision
    reason: str
    extension_id: str


def evaluate(
    info: ExtensionInfo,
    allowlist_publishers: list[str],
    allowlist_extensions: list[str],
    blocklist_extensions: set[str],
) -> PolicyResult:
    """Apply policy rules to an extension.

    Order of precedence:
        1. Blocklist hit → BLOCK (always wins)
        2. Allowlist hit → ALLOW
        3. Verified publisher → ALLOW
        4. Otherwise → BLOCK
    """
    ext_id = f"{info.publisher_id}.{info.extension_name}".lower()

    if ext_id in blocklist_extensions:
        return PolicyResult(Decision.BLOCK, "extension on RemovedPackages blocklist", ext_id)

    if ext_id in {e.lower() for e in allowlist_extensions}:
        return PolicyResult(Decision.ALLOW, "extension on allowlist", ext_id)

    if info.publisher_id.lower() in {p.lower() for p in allowlist_publishers}:
        return PolicyResult(Decision.ALLOW, "publisher on allowlist", ext_id)

    if info.is_verified:
        return PolicyResult(Decision.ALLOW, "publisher is verified", ext_id)

    return PolicyResult(Decision.BLOCK, "publisher is not verified", ext_id)