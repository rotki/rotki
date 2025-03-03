import logging
from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_VELODROME
from rotkehlchen.chain.evm.decoding.velodrome.decoder import VelodromeLikeDecoder
from rotkehlchen.chain.evm.decoding.velodrome.velodrome_cache import (
    read_velodrome_pools_and_gauges_from_cache,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import VELODROME_POOL_PROTOCOL, CacheType

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.optimism.manager import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


ROUTER_V2: Final = string_to_evm_address('0xa062aE8A9c5e11aaA026fc2670B0D65cCc8B2858')
ROUTER_V1: Final = string_to_evm_address('0x9c12939390052919aF3155f41Bf4160Fd3666A6f')


class VelodromeDecoder(VelodromeLikeDecoder):

    def __init__(
            self,
            optimism_inquirer: 'OptimismInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=optimism_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            counterparty=CPT_VELODROME,
            routers={ROUTER_V1, ROUTER_V2},
            token_symbol='VELO',
            voter_address=string_to_evm_address('0x41C914ee0c7E1A5edCD0295623e6dC557B5aBf3C'),
            voting_escrow_address=string_to_evm_address('0xFAf8FD17D9840595845582fCB047DF13f006787d'),
            gauge_fees_cache_type=CacheType.VELODROME_GAUGE_FEE_ADDRESS,
            gauge_bribes_cache_type=CacheType.VELODROME_GAUGE_BRIBE_ADDRESS,
            pool_cache_type=CacheType.VELODROME_POOL_ADDRESS,
            read_fn=read_velodrome_pools_and_gauges_from_cache,
            pool_token_protocol=VELODROME_POOL_PROTOCOL,
        )

    @staticmethod
    def possible_products() -> dict[str, list[EvmProduct]]:
        return {
            CPT_VELODROME: [EvmProduct.POOL, EvmProduct.GAUGE],
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_VELODROME, label='velodrome_finance', image='velodrome.svg'),)  # noqa: E501
