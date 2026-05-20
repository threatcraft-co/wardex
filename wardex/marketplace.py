"""Visual Studio Marketplace API client.

Queries the marketplace REST endpoint to determine whether a given extension's
publisher holds verified status (the blue checkmark).

Marketplace publisherFlags bitmask:
    1 = Disabled
    2 = Verified (legacy)
    4 = Verified / Trusted publisher (blue checkmark)
    8 = Certified
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)

MARKETPLACE_URL = "https://marketplace.visualstudio.com/_apis/public/gallery/extensionquery"
API_VERSION = "7.2-preview.1"
VERIFIED_PUBLISHER_FLAG = 4
DEFAULT_TIMEOUT = 10


@dataclass
class ExtensionInfo:
    """Metadata about an extension returned from the Marketplace."""

    publisher_id: str
    publisher_display_name: str
    extension_name: str
    publisher_flags: int
    latest_version: Optional[str]
    last_updated: Optional[str]

    @property
    def is_verified(self) -> bool:
        """Whether the publisher holds the verified (blue check) badge."""
        return bool(self.publisher_flags & VERIFIED_PUBLISHER_FLAG)


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

        return ExtensionInfo(
            publisher_id=publisher.get("publisherName", ""),
            publisher_display_name=publisher.get("displayName", ""),
            extension_name=ext.get("extensionName", ""),
            publisher_flags=publisher.get("flags", 0)
            if isinstance(publisher.get("flags"), int)
            else self._parse_flags(publisher.get("flags", "")),
            latest_version=latest.get("version"),
            last_updated=latest.get("lastUpdated"),
        )

    @staticmethod
    def _parse_flags(flags) -> int:
        """The flags field can come back as a string like 'verified, public'.

        Map the relevant string tokens to the bitmask values we care about.
        """
        if isinstance(flags, int):
            return flags
        if not isinstance(flags, str):
            return 0
        value = 0
        tokens = [t.strip().lower() for t in flags.split(",")]
        if "verified" in tokens:
            value |= VERIFIED_PUBLISHER_FLAG
        if "disabled" in tokens:
            value |= 1
        if "certified" in tokens:
            value |= 8
        return value