"""Tests for the policy engine."""

from wardex.marketplace import ExtensionInfo
from wardex.policy import Decision, evaluate


def _info(publisher: str, name: str, verified: bool) -> ExtensionInfo:
    return ExtensionInfo(
        publisher_id=publisher,
        publisher_display_name=publisher,
        extension_name=name,
        is_domain_verified=verified,
        verified_domain="example.com" if verified else None,
        is_publisher_flagged_verified=False,
        latest_version="1.0.0",
        last_updated=None,
    )


def test_verified_publisher_allowed():
    result = evaluate(_info("ms-python", "python", True), [], [], set())
    assert result.decision == Decision.ALLOW


def test_unverified_publisher_blocked():
    result = evaluate(_info("randomuser", "thing", False), [], [], set())
    assert result.decision == Decision.BLOCK


def test_allowlist_overrides_unverified():
    result = evaluate(_info("randomuser", "thing", False), ["randomuser"], [], set())
    assert result.decision == Decision.ALLOW


def test_blocklist_overrides_verified():
    result = evaluate(_info("ms-python", "python", True), [], [], {"ms-python.python"})
    assert result.decision == Decision.BLOCK