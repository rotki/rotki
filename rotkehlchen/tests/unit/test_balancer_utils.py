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


def test_beets_cache_and_version_mappings() -> None:
    """Beets counterparties must resolve to the Balancer v2/v3 pools cache and versions."""
    from rotkehlchen.chain.evm.decoding.balancer.constants import (
        BALANCER_CACHE_TYPE_MAPPING,
        BALANCER_VERSION_MAPPING,
        CPT_BEETS_V2,
        CPT_BEETS_V3,
    )
    from rotkehlchen.types import CacheType

    assert BALANCER_CACHE_TYPE_MAPPING[CPT_BEETS_V2] == CacheType.BALANCER_V2_POOLS
    assert BALANCER_CACHE_TYPE_MAPPING[CPT_BEETS_V3] == CacheType.BALANCER_V3_POOLS
    assert BALANCER_VERSION_MAPPING[CPT_BEETS_V2] == 2
    assert BALANCER_VERSION_MAPPING[CPT_BEETS_V3] == 3


def test_beets_counterparties() -> None:
    """The Sonic Beets decoders must surface the Beets label and icon."""
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.balancer.constants import CPT_BEETS_V2, CPT_BEETS_V3
    from rotkehlchen.chain.sonic.modules.balancer.v2.decoder import Balancerv2Decoder
    from rotkehlchen.chain.sonic.modules.balancer.v3.decoder import Balancerv3Decoder

    assert Balancerv2Decoder.counterparties() == (CounterpartyDetails(
        identifier=CPT_BEETS_V2,
        label='Beets',
        image='beets.svg',
    ),)
    assert Balancerv3Decoder.counterparties() == (CounterpartyDetails(
        identifier=CPT_BEETS_V3,
        label='Beets',
        image='beets.svg',
    ),)


def test_balancer_api_chain_mapping_contains_sonic() -> None:
    assert CHAIN_ID_TO_BALANCER_API_MAPPINGS[ChainID.SONIC] == 'SONIC'


def test_balancer_api_chain_mapping_contains_hyperevm() -> None:
    assert CHAIN_ID_TO_BALANCER_API_MAPPINGS[ChainID.HYPERLIQUID] == 'HYPEREVM'


def test_query_balancer_pools_count_unsupported_chain() -> None:
    with pytest.raises(RemoteError, match='Balancer API does not support chain'):
        query_balancer_pools_count(chain=ChainID.BINANCE_SC, version=3)


def test_query_balancer_pools_unsupported_chain() -> None:
    with pytest.raises(RemoteError, match='Balancer API does not support chain'):
        query_balancer_pools(chain=ChainID.BINANCE_SC, version=3)
