import logging
from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_AERODROME
from rotkehlchen.chain.evm.decoding.velodrome.decoder import VelodromeLikeDecoder
from rotkehlchen.chain.evm.decoding.velodrome.velodrome_cache import (
    read_aerodrome_pools_and_gauges_from_cache,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import AERODROME_POOL_PROTOCOL, CacheType

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


ROUTER: Final = string_to_evm_address('0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43')


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
            voter_address=string_to_evm_address('0x16613524e02ad97eDfeF371bC883F2F5d6C480A5'),
            voting_escrow_address=string_to_evm_address('0xeBf418Fe2512e7E6bd9b87a8F0f294aCDC67e6B4'),
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
        return (CounterpartyDetails(identifier=CPT_AERODROME, label='Aerodrome Finance', image='aerodrome.svg'),)  # noqa: E501
