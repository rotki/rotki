import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.quickswap.constants import CPT_QUICKSWAP_V4
from rotkehlchen.chain.evm.decoding.quickswap.v3.decoder import Quickswapv3LikeLPDecoder
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.uniswap.v4.utils import decode_uniswap_v4_like_swaps
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

from .constants import CPT_QUICKSWAP_V4_ROUTER, QUICKSWAP_SWAP_TOPIC, QUICKSWAP_V4_NFT_MANAGER_ABI

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Quickswapv4CommonDecoder(Quickswapv3LikeLPDecoder):
    """Common decoder for Quickswap v4.
    Quickswap V4 is actually more closely related to Uniswap V3 than V4 despite the version number.
    So we inherit from Quickswapv3LikeLPDecoder which handles the Uniswap V3 like LP decoding but
    use decode_uniswap_v4_like_swaps to decode the swaps which are slightly different from both
    Uniswap V3 and V4, but can still be handled by the V4 function.
    """

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            swap_router: 'ChecksumEvmAddress',
            nft_manager: 'ChecksumEvmAddress',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            nft_manager=nft_manager,
            nft_manager_abi=QUICKSWAP_V4_NFT_MANAGER_ABI,
            counterparty=CPT_QUICKSWAP_V4,
            version_string='V4',
        )
        self.swap_router = swap_router

    def _router_post_decoding(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        """Decode swaps routed through the Quickswap v4 router."""
        return decode_uniswap_v4_like_swaps(
            transaction=transaction,
            decoded_events=decoded_events,
            all_logs=all_logs,
            base_tools=self.base,
            swap_topics=(QUICKSWAP_SWAP_TOPIC,),
            counterparty=CPT_QUICKSWAP_V4,
            router_address=self.swap_router,
            wrapped_native_currency=self.wrapped_native_currency,
        )

    # -- DecoderInterface methods

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return super().post_decoding_rules() | {
            CPT_QUICKSWAP_V4_ROUTER: [(0, self._router_post_decoding)],
        }

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {self.swap_router: CPT_QUICKSWAP_V4_ROUTER}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails.from_versioned_counterparty(
            counterparty=CPT_QUICKSWAP_V4,
            image='quickswap.png',
        ),)
