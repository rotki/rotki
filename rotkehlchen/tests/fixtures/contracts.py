from typing import Literal

import pytest

from rotkehlchen.chain.evm.contracts import EvmContracts
from rotkehlchen.types import ChainID


@pytest.fixture(name='evm_contracts')
def fixture_evm_contracts():  # noqa: PT004  # adding leading underscore does not return it
    """Initialize the common EvmContracts ABIs"""
    EvmContracts.initialize_common_abis()


@pytest.fixture(name='ethereum_contracts')
def fixture_ethereum_contracts(evm_contracts):  # pylint: disable=unused-argument
    return EvmContracts[Literal[ChainID.ETHEREUM]](ChainID.ETHEREUM)
