"""Placeholder update service interface for future auto-update support."""

from __future__ import annotations


class UpdateService:
    """Provide hooks for checking, downloading, and installing updates."""

    def check_for_updates(self) -> bool:
        """Return True when an update is available."""
        return False

    def download_update(self) -> bool:
        """Download the latest update package."""
        return False

    def install_update(self) -> bool:
        """Install the downloaded update package."""
        return False
