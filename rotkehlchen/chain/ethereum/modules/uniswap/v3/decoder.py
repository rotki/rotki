from typing import Callable, List, Optional

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.types import EthereumTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from ..constants import CPT_UNISWAP_V3

# https://www.4byte.directory/api/v1/event-signatures/?hex_signature=0xc42079f94a6350d7e6235f29174924f928cc2ac818eb64fed8004e115fbcca67  # noqa: E501
SWAP_SIGNATURE = b'\xc4 y\xf9JcP\xd7\xe6#_)\x17I$\xf9(\xcc*\xc8\x18\xebd\xfe\xd8\x00N\x11_\xbc\xcag'  # noqa: E501


class Uniswapv3Decoder(DecoderInterface):  # lgtm[py/missing-call-to-init]

    def _maybe_decode_v3_swap(  # pylint: disable=no-self-use
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> None:
        """Search for both events. Since the order is not guaranteed try reshuffle in both cases"""
        out_event = in_event = None
        if tx_log.topics[0] == SWAP_SIGNATURE:
            buyer = hex_or_bytes_to_address(tx_log.topics[2])
            # the amount returned in the event is negative as it is the amount leaving the pool
            amount_received = abs(hex_or_bytes_to_int(tx_log.data[0:32], signed=True))
            amount_sent = hex_or_bytes_to_int(tx_log.data[32:64])
            for event in decoded_events:
                if (
                    event.event_type == HistoryEventType.SPEND and
                    event.location_label == buyer and
                    event.balance.amount == asset_normalized_value(amount=amount_sent, asset=event.asset)  # noqa: E501
                ):
                    event.event_type = HistoryEventType.TRADE
                    event.event_subtype = HistoryEventSubType.SPEND
                    event.counterparty = CPT_UNISWAP_V3
                    event.notes = f'Swap {event.balance.amount} {event.asset.symbol} in uniswap-v3 from {event.location_label}'  # noqa: E501
                    out_event = event
                elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.location_label == buyer and
                    event.balance.amount == asset_normalized_value(amount=amount_received, asset=event.asset)  # noqa: E501
                ):
                    event.event_type = HistoryEventType.TRADE
                    event.event_subtype = HistoryEventSubType.RECEIVE
                    event.counterparty = CPT_UNISWAP_V3
                    event.notes = f'Receive {event.balance.amount} {event.asset.symbol} in uniswap-v3 from {event.location_label}'  # noqa: E501
                    in_event = event
        maybe_reshuffle_events(out_event=out_event, in_event=in_event)

    # -- DecoderInterface methods

    def decoding_rules(self) -> List[Callable]:
        return [
            self._maybe_decode_v3_swap,
        ]

    def counterparties(self) -> List[str]:
        return [CPT_UNISWAP_V3]
