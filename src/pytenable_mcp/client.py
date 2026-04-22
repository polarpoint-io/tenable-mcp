"""Lazy-initialised pyTenable client factory.

Reads credentials from environment variables at first use so that
import of this module never fails simply because env vars are unset
(useful for tests, linting and Docker image build).
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from tenable.io import TenableIO


class TenableConfigError(RuntimeError):
    """Raised when Tenable.io credentials are missing or invalid."""


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise TenableConfigError(
            f"Environment variable {name} is required. "
            "Set TIO_ACCESS_KEY and TIO_SECRET_KEY to your Tenable.io API keys."
        )
    return value


@lru_cache(maxsize=1)
def get_client() -> "TenableIO":
    """Return a cached TenableIO client built from env vars."""
    # Imported lazily so the module can load even if pyTenable is not yet
    # installed (helpful during container builds and unit tests).
    from tenable.io import TenableIO

    access_key = _require_env("TIO_ACCESS_KEY")
    secret_key = _require_env("TIO_SECRET_KEY")
    url = os.environ.get("TIO_URL", "https://cloud.tenable.com")
    vendor = os.environ.get("TIO_VENDOR", "pytenable-mcp")
    product = os.environ.get("TIO_PRODUCT", "pytenable-mcp")
    build = os.environ.get("TIO_BUILD", "0.1.0")

    return TenableIO(
        access_key=access_key,
        secret_key=secret_key,
        url=url,
        vendor=vendor,
        product=product,
        build=build,
    )


def reset_client() -> None:
    """Clear the cached client (primarily for testing)."""
    get_client.cache_clear()
