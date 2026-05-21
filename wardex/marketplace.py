"""Visual Studio Marketplace API client.

Queries the Marketplace REST endpoint to determine whether an extension's
publisher is trustworthy. We distinguish two trust signals the Marketplace
exposes, because they are NOT the same thing:

    1. publisher.flags == "verified"
       Indicates the publisher account is in good standing (account age,
       no policy violations). This is a weak signal — many indie and
       random publishers qualify after enough time.

    2. publisher.isDomainVerified == true
       Indicates the publisher proved ownership of a real domain (e.g.,
       microsoft.com, github.com). This is what renders as the BLUE
       CHECKMARK BADGE on the Marketplace website. This is the strong
       signal users actually visually identify as "verified."

Wardex uses domain verification as the primary trust signal. Publisher-
flags "verified" is exposed as a secondary signal for advanced policy
authoring (e.g., a security team that wants to allow account-in-good-
standing publishers from a specific allowlist while still requiring
domain verification by default).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)

MARKETPLACE_URL = "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery"
API_VERSION = "7.2-preview.1"

# Legacy publisher-flags bitmask — kept for parsing only.
PUBLISHER_FLAG_DISABLED = 1
PUBLISHER_FLAG_VERIFIED_LEGACY = 4   # account in good standing — NOT the blue check
PUBLISHER_FLAG_CERTIFIED = 8

DEFAULT_TIMEOUT = 10


@dataclass
class ExtensionInfo:
    """Metadata about an extension returned from the Marketplace."""

    publisher_id: str
    publisher_display_name: str
    extension_name: str

    # Strong signal — the blue checkmark.
    is_domain_verified: bool
    verified_domain: Optional[str]

    # Weak signal — account in good standing.
    is_publisher_flagged_verified: bool

    latest_version: Optional[str]
    last_updated: Optional[str]

    @property
    def is_verified(self) -> bool:
        """Primary trust signal used by policy: blue-checkmark only.

        Policy.evaluate() reads this. Domain verification is the only
        verification that maps to what users see on the Marketplace page.
        """
        return self.is_domain_verified


class MarketplaceError(Exception):
    """Raised when the Marketplace API cannot be queried."""


class MarketplaceClient:
    """Thin client over the VS Code Marketplace extensionquery API."""

    def __init__(self, timeout: int = DEFAULT_TIMEOUT):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
                "Accept": f"application/json;api-version={API_VERSION}",
                "User-Agent": "wardex/0.1.0",
            }
        )

    def fetch_extension(self, extension_id: str) -> ExtensionInfo:
        """Look up an extension by its fully-qualified id (`publisher.name`).

        Raises MarketplaceError if the extension is not found or the API fails.
        """
        payload = {
            "filters": [
                {
                    "criteria": [{"filterType": 7, "value": extension_id}],
                    "pageNumber": 1,
                    "pageSize": 1,
                }
            ],
            "flags": 914,
        }

        try:
            resp = self.session.post(MARKETPLACE_URL, json=payload, timeout=self.timeout)
            resp.raise_for_status()
        except requests.RequestException as e:
            logger.error("Marketplace API request failed: %s", e)
            raise MarketplaceError(f"API request failed: {e}") from e

        data = resp.json()
        results = data.get("results", [])
        if not results or not results[0].get("extensions"):
            raise MarketplaceError(f"Extension not found: {extension_id}")

        ext = results[0]["extensions"][0]
        publisher = ext.get("publisher", {})
        versions = ext.get("versions", [])
        latest = versions[0] if versions else {}

        # Domain verification is the strong signal.
        is_domain_verified = bool(publisher.get("isDomainVerified", False))
        verified_domain = publisher.get("domain")

        # Publisher-flags "verified" is the weak signal.
        is_publisher_flagged_verified = self._parse_publisher_flag_verified(
            publisher.get("flags")
        )

        return ExtensionInfo(
            publisher_id=publisher.get("publisherName", ""),
            publisher_display_name=publisher.get("displayName", ""),
            extension_name=ext.get("extensionName", ""),
            is_domain_verified=is_domain_verified,
            verified_domain=verified_domain,
            is_publisher_flagged_verified=is_publisher_flagged_verified,
            latest_version=latest.get("version"),
            last_updated=latest.get("lastUpdated"),
        )

    @staticmethod
    def _parse_publisher_flag_verified(flags) -> bool:
        """The flags field may be an int bitmask or a comma-separated string.

        Returns True only for the legacy publisher-flags 'verified' bit. This
        is NOT the blue checkmark — for that, use isDomainVerified.
        """
        if isinstance(flags, int):
            return bool(flags & PUBLISHER_FLAG_VERIFIED_LEGACY)
        if isinstance(flags, str):
            tokens = [t.strip().lower() for t in flags.split(",")]
            return "verified" in tokens
        return False