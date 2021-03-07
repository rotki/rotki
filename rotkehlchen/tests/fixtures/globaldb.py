from typing import List, Optional

import pytest

from rotkehlchen.chain.ethereum.typing import CustomEthereumToken
from rotkehlchen.globaldb import GlobalDBHandler


@pytest.fixture(name='custom_ethereum_tokens')
def fixture_custom_ethereum_tokens() -> Optional[List[CustomEthereumToken]]:
    return None


def create_globaldb(
        data_directory,
) -> GlobalDBHandler:
    # Since this is a singleton and we want it initialized everytime the fixture
    # is called make sure its instance is always starting from scratch
    GlobalDBHandler._GlobalDBHandler__instance = None  # type: ignore

    handler = GlobalDBHandler(data_dir=data_directory)
    # note: the addition of custom ethereum tokens is moved after resolver initialization
    # so that DB can be primed with all assets.json
    return handler


@pytest.fixture(name='globaldb')
def fixture_globaldb(data_dir):
    return create_globaldb(data_directory=data_dir)
