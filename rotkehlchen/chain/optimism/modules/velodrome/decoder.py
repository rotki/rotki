import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_VELODROME
from rotkehlchen.chain.evm.decoding.velodrome.decoder import VelodromeLikeDecoder
from rotkehlchen.chain.evm.decoding.velodrome.velodrome_cache import (
    read_velodrome_pools_and_gauges_from_cache,
)
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import CacheType

from .constants import ROUTER_V1, ROUTER_V2, VOTER_CONTRACT_ADDRESS, VOTING_ESCROW_CONTRACT_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.optimism.manager import OptimismInquirer
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


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
            voter_address=VOTER_CONTRACT_ADDRESS,
            voting_escrow_address=VOTING_ESCROW_CONTRACT_ADDRESS,
            gauge_fees_cache_type=CacheType.VELODROME_GAUGE_FEE_ADDRESS,
            gauge_bribes_cache_type=CacheType.VELODROME_GAUGE_BRIBE_ADDRESS,
            pool_cache_type=CacheType.VELODROME_POOL_ADDRESS,
            read_fn=read_velodrome_pools_and_gauges_from_cache,
        )

    @staticmethod
    def possible_products() -> dict[str, list[EvmProduct]]:
        return {
            CPT_VELODROME: [EvmProduct.POOL, EvmProduct.GAUGE],
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_VELODROME, label='Velodrome Finance', image='velodrome.png'),)  # noqa: E501
