from collections.abc import Generator

import pytest

from rotkehlchen.mcp.backend import configure_backend, get_backend_config


@pytest.fixture(autouse=True)
def restore_backend_config() -> Generator[None]:
    backend_config = get_backend_config()
    yield
    configure_backend(base_url=backend_config.base_url, timeout=backend_config.timeout)
