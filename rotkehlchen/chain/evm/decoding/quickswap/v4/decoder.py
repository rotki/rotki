import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from rotkehlchen.assets.utils import CHAIN_TO_WRAPPED_TOKEN
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.quickswap.constants import CPT_QUICKSWAP_V4
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.uniswap.v4.utils import decode_uniswap_v4_like_swaps
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

from .constants import QUICKSWAP_SWAP_TOPIC

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import EvmTransaction
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Quickswapv4CommonDecoder(DecoderInterface):

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            swap_router: 'ChecksumEvmAddress',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.wrapped_native_currency = CHAIN_TO_WRAPPED_TOKEN[evm_inquirer.blockchain]
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
        return {CPT_QUICKSWAP_V4: [(0, self._router_post_decoding)]}

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return {self.swap_router: CPT_QUICKSWAP_V4}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails.from_versioned_counterparty(
            counterparty=CPT_QUICKSWAP_V4,
            image='quickswap.png',
        ),)
