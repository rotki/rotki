from typing import Literal

import pytest

from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.types import ChainID


@pytest.fixture(name='ethereum_contracts')
def fixture_ethereum_contracts():
    return EvmContracts[Literal[ChainID.ETHEREUM]](ChainID.ETHEREUM)
