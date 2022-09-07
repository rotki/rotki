from typing import Callable, List, Optional

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.types import EthereumTransaction
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from ..constants import CPT_UNISWAP_V2

# https://www.4byte.directory/api/v1/event-signatures/?hex_signature=0xd78ad95fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822  # noqa: E501
SWAP_SIGNATURE = b'\xd7\x8a\xd9_\xa4l\x99KeQ\xd0\xda\x85\xfc\'_\xe6\x13\xce7e\x7f\xb8\xd5\xe3\xd10\x84\x01Y\xd8"'  # noqa: E501


class Uniswapv2Decoder(DecoderInterface):  # lgtm[py/missing-call-to-init]

    def _maybe_decode_v2_swap(  # pylint: disable=no-self-use
            self,
            token: Optional[EvmToken],  # pylint: disable=unused-argument
            tx_log: EthereumTxReceiptLog,
            transaction: EthereumTransaction,  # pylint: disable=unused-argument
            decoded_events: List[HistoryBaseEntry],
            action_items: List[ActionItem],  # pylint: disable=unused-argument
    ) -> None:
        """Decode trade for uniswap v2. The approach is to read the events and detect the ones
        where the user sends and receives any asset. The spend asset is the swap executed and
        the received is the result of calling the swap method in the uniswap contract.
        We need to make sure that the events related to the swap are consecutive and for that
        we make use of the maybe_reshuffle_events.
        """
        if tx_log.topics[0] == SWAP_SIGNATURE:
            # When the router chains multiple swaps in one transaction only the last swap has
            # the buyer in the topic. In that case we know it is the last swap and the receiver is
            # the user
            maybe_buyer = hex_or_bytes_to_address(tx_log.topics[2])
            out_event = in_event = None

            # amount_in is the amount that enters the pool and amount_out the one
            # that leaves the pool
            amount_in_0, amount_in_1 = hex_or_bytes_to_int(tx_log.data[0:32]), hex_or_bytes_to_int(tx_log.data[32:64])  # noqa: E501
            amount_out_0, amount_out_1 = hex_or_bytes_to_int(tx_log.data[64:96]), hex_or_bytes_to_int(tx_log.data[96:128])  # noqa: E501
            amount_in, amount_out = amount_in_0, amount_out_0
            if amount_in == ZERO:
                amount_in = amount_in_1
            if amount_out == ZERO:
                amount_out = amount_out_1

            received_eth = ZERO
            for event in decoded_events:
                if event.asset == A_ETH and event.event_type == HistoryEventType.RECEIVE:
                    received_eth += event.balance.amount

            for event in decoded_events:
                # When we look for the spend event we have to take into consideration the case
                # where not all the ETH is converted. The ETH that is not converted is returned
                # in an internal transaction to the user.
                if (
                    event.event_type == HistoryEventType.SPEND and
                    (
                        event.balance.amount == (spend_eth := asset_normalized_value(amount_in, event.asset)) or  # noqa: E501
                        event.asset == A_ETH and spend_eth + received_eth == event.balance.amount
                    )
                ):
                    event.event_type = HistoryEventType.TRADE
                    event.event_subtype = HistoryEventSubType.SPEND
                    event.counterparty = CPT_UNISWAP_V2
                    event.notes = f'Swap {event.balance.amount} {event.asset.symbol} in uniswap-v2 from {event.location_label}'  # noqa: E501
                    out_event = event
                elif (
                    (maybe_buyer == transaction.from_address or event.asset == A_ETH) and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.balance.amount == asset_normalized_value(amount_out, event.asset)
                ):
                    event.event_type = HistoryEventType.TRADE
                    event.event_subtype = HistoryEventSubType.RECEIVE
                    event.counterparty = CPT_UNISWAP_V2
                    event.notes = f'Receive {event.balance.amount} {event.asset.symbol} in uniswap-v2 from {event.location_label}'  # noqa: E501
                    in_event = event
                elif (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.balance.amount != asset_normalized_value(amount_out, event.asset)
                ):
                    # Those are assets returned due to a change in the swap price
                    event.event_type = HistoryEventType.TRANSFER
                    event.counterparty = CPT_UNISWAP_V2
                    event.notes = f'Refund of {event.balance.amount} {event.asset.symbol} in uniswap-v2 due to price change'  # noqa: E501

            maybe_reshuffle_events(out_event=out_event, in_event=in_event)

    # -- DecoderInterface methods

    def decoding_rules(self) -> List[Callable]:
        return [
            self._maybe_decode_v2_swap,
        ]

    def counterparties(self) -> List[str]:
        return [CPT_UNISWAP_V2]
