import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.decoding.weth.decoder import (
    WETH_WITHDRAW_TOPIC,
    WethDecoder as EthBaseWethDecoder,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import EvmTransaction


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class WethDecoder(EthBaseWethDecoder):
    def _maybe_add_base_fallback_unwrap(
            self,
            transaction: 'EvmTransaction',
            decoded_events: list['EvmEvent'],
            all_logs: list['EvmTxReceiptLog'],
    ) -> list['EvmEvent']:
        if not self.base.is_tracked(transaction.from_address):
            return decoded_events

        if any(
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.RETURN_WRAPPED and
                event.asset == self.wrapped_token and
                event.counterparty == self.counterparty
                for event in decoded_events
        ):
            return decoded_events

        non_fee_events = [
            event for event in decoded_events
            if not (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.FEE
            ) and event.event_type != HistoryEventType.INFORMATIONAL
        ]

        for tx_log in all_logs:
            if tx_log.address != self.wrapped_token.evm_address:
                continue
            if tx_log.topics[0] != WETH_WITHDRAW_TOPIC:
                continue
            if self.base.is_tracked(bytes_to_address(tx_log.topics[1])):
                continue

            withdrawn_amount = asset_normalized_value(
                amount=int.from_bytes(tx_log.data[:32]),
                asset=self.base_asset,
            )
            for event in non_fee_events:
                if (
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == self.base_asset and
                    event.amount == withdrawn_amount and
                    event.location_label == transaction.from_address
                ):
                    if len(non_fee_events) != 1:
                        return decoded_events

                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                    event.counterparty = self.counterparty
                    event.notes = f'Receive {withdrawn_amount} {self.base_asset.symbol}'

                    out_event = self.base.make_event_next_index(
                        tx_ref=transaction.tx_hash,
                        timestamp=transaction.timestamp,
                        event_type=HistoryEventType.SPEND,
                        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
                        asset=self.wrapped_token,
                        amount=withdrawn_amount,
                        location_label=transaction.from_address,
                        counterparty=self.counterparty,
                        notes=f'Unwrap {withdrawn_amount} {self.wrapped_token.symbol}',
                        address=self.wrapped_token.evm_address,
                    )
                    decoded_events.append(out_event)
                    maybe_reshuffle_events(
                        ordered_events=[out_event, event],
                        events_list=decoded_events,
                    )
                    return decoded_events

        return decoded_events

    def post_decoding_rules(self) -> dict[str, list[tuple[int, Callable]]]:
        return {self.counterparty: [(0, self._maybe_add_base_fallback_unwrap)]}
