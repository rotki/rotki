import logging
from typing import TYPE_CHECKING, Callable, Optional

from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.aave.v1.decoder import DEFAULT_DECODING_OUTPUT
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import ActionItem, DecodingOutput
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails, EventCategory
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import DecoderEventMappingType, EvmTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address

from ..constants import CPT_UNISWAP_V1, UNISWAP_ICON, UNISWAP_LABEL

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# https://github.com/Uniswap/v1-contracts/blob/c10c08d81d6114f694baa8bd32f555a40f6264da/contracts/uniswap_exchange.vy#L13
TOKEN_PURCHASE = b'\xcd`\xaau\xde\xa3\x07/\xbc\x07\xaem}\x85k]\xc5\xf4\xee\xe8\x88T\xf5\xb4\xab\xf7\xb6\x80\xef\x8b\xc5\x0f'  # noqa: E501
# https://github.com/Uniswap/v1-contracts/blob/c10c08d81d6114f694baa8bd32f555a40f6264da/contracts/uniswap_exchange.vy#L14
ETH_PURCHASE = b'\x7f@\x91\xb4l3\xe9\x18\xa0\xf3\xaaB0vA\xd1{\xb6p)BzSi\xe5K59\x84#\x87\x05'  # noqa: E501


class Uniswapv1Decoder(DecoderInterface):

    def _maybe_decode_swap(
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EvmTxReceiptLog,
            transaction: EvmTransaction,  # pylint: disable=unused-argument
            decoded_events: list['EvmEvent'],
            action_items: list[ActionItem],  # pylint: disable=unused-argument
            all_logs: list[EvmTxReceiptLog],  # pylint: disable=unused-argument
    ) -> DecodingOutput:
        """Search for both events. Since the order is not guaranteed try reshuffle in both cases"""
        out_event = in_event = None
        if tx_log.topics[0] == TOKEN_PURCHASE:
            buyer = hex_or_bytes_to_address(tx_log.topics[1])
            # search for a send to buyer from a tracked address
            for event in decoded_events:
                if event.event_type == HistoryEventType.SPEND and event.address == buyer:
                    try:
                        crypto_asset = event.asset.resolve_to_crypto_asset()
                    except (UnknownAsset, WrongAssetType):
                        self.notify_user(event=event, counterparty=CPT_UNISWAP_V1)
                        continue
                    event.event_type = HistoryEventType.TRADE
                    event.event_subtype = HistoryEventSubType.SPEND
                    event.counterparty = CPT_UNISWAP_V1
                    event.notes = f'Swap {event.balance.amount} {crypto_asset.symbol} in uniswap-v1 from {event.location_label}'  # noqa: E501
                    out_event = event
                elif event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.RECEIVE and event.counterparty == CPT_UNISWAP_V1:  # noqa: :E501
                    in_event = event

        elif tx_log.topics[0] == ETH_PURCHASE:
            buyer = hex_or_bytes_to_address(tx_log.topics[1])
            # search for a receive to buyer
            for event in decoded_events:
                if event.event_type == HistoryEventType.RECEIVE and event.location_label == buyer:
                    try:
                        crypto_asset = event.asset.resolve_to_crypto_asset()
                    except (UnknownAsset, WrongAssetType):
                        self.notify_user(event=event, counterparty=CPT_UNISWAP_V1)
                        continue
                    event.event_type = HistoryEventType.TRADE
                    event.event_subtype = HistoryEventSubType.RECEIVE
                    event.counterparty = CPT_UNISWAP_V1
                    event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} from uniswap-v1 swap in {event.location_label}'  # noqa: E501
                    in_event = event
                elif event.event_type == HistoryEventType.TRADE and event.event_subtype == HistoryEventSubType.SPEND and event.counterparty == CPT_UNISWAP_V1:  # noqa: :E501
                    out_event = event

        maybe_reshuffle_events(ordered_events=[out_event, in_event], events_list=decoded_events)
        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def possible_events(self) -> DecoderEventMappingType:
        return {CPT_UNISWAP_V1: {
            HistoryEventType.TRADE: {
                HistoryEventSubType.RECEIVE: EventCategory.SWAP_IN,
                HistoryEventSubType.SPEND: EventCategory.SWAP_OUT,
            },
        }}

    def decoding_rules(self) -> list[Callable]:
        return [
            self._maybe_decode_swap,
        ]

    def counterparties(self) -> list[CounterpartyDetails]:
        return [CounterpartyDetails(
            identifier=CPT_UNISWAP_V1,
            label=UNISWAP_LABEL,
            image=UNISWAP_ICON,
        )]
