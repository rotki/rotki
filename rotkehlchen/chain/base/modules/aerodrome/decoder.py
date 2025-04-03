import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_AERODROME
from rotkehlchen.chain.evm.decoding.velodrome.decoder import VelodromeLikeDecoder
from rotkehlchen.chain.evm.decoding.velodrome.velodrome_cache import (
    read_aerodrome_pools_and_gauges_from_cache,
)
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import AERODROME_POOL_PROTOCOL, CacheType

from .constants import ROUTER, VOTER_CONTRACT_ADDRESS, VOTING_ESCROW_CONTRACT_ADDRESS

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AerodromeDecoder(VelodromeLikeDecoder):

    def __init__(
            self,
            base_inquirer: 'BaseInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=base_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            counterparty=CPT_AERODROME,
            routers={ROUTER},
            token_symbol='AERO',
            voter_address=VOTER_CONTRACT_ADDRESS,
            voting_escrow_address=VOTING_ESCROW_CONTRACT_ADDRESS,
            gauge_fees_cache_type=CacheType.AERODROME_GAUGE_FEE_ADDRESS,
            gauge_bribes_cache_type=CacheType.AERODROME_GAUGE_BRIBE_ADDRESS,
            pool_cache_type=CacheType.AERODROME_POOL_ADDRESS,
            read_fn=read_aerodrome_pools_and_gauges_from_cache,
            pool_token_protocol=AERODROME_POOL_PROTOCOL,
        )

    @staticmethod
    def possible_products() -> dict[str, list[EvmProduct]]:
        return {
            CPT_AERODROME: [EvmProduct.POOL, EvmProduct.GAUGE],
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_AERODROME, label='Aerodrome Finance', image='aerodrome.png'),)  # noqa: E501
