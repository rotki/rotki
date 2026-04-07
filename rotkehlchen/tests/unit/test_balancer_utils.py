import pytest

from rotkehlchen.chain.evm.decoding.balancer.constants import CHAIN_ID_TO_BALANCER_API_MAPPINGS
from rotkehlchen.chain.evm.decoding.balancer.utils import (
    query_balancer_pools,
    query_balancer_pools_count,
)
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.types import ChainID


def test_balancer_api_chain_mapping_contains_monad() -> None:
    assert CHAIN_ID_TO_BALANCER_API_MAPPINGS[ChainID.MONAD] == 'MONAD'


def test_balancer_api_chain_mapping_contains_hyperevm() -> None:
    assert CHAIN_ID_TO_BALANCER_API_MAPPINGS[ChainID.HYPERLIQUID] == 'HYPEREVM'


def test_query_balancer_pools_count_unsupported_chain() -> None:
    with pytest.raises(RemoteError, match='Balancer API does not support chain'):
        query_balancer_pools_count(chain=ChainID.BINANCE_SC, version=3)


def test_query_balancer_pools_unsupported_chain() -> None:
    with pytest.raises(RemoteError, match='Balancer API does not support chain'):
        query_balancer_pools(chain=ChainID.BINANCE_SC, version=3)
