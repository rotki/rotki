from abc import ABC
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.chain.ethereum.modules.weth.constants import CPT_WETH
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


WETH_DEPOSIT_TOPIC = b'\xe1\xff\xfc\xc4\x92=\x04\xb5Y\xf4\xd2\x9a\x8b\xfcl\xda\x04\xeb[\r<F\x07Q\xc2@,\\\\\xc9\x10\x9c'  # noqa: E501
WETH_WITHDRAW_TOPIC = b'\x7f\xcfS,\x15\xf0\xa6\xdb\x0b\xd6\xd0\xe08\xbe\xa7\x1d0\xd8\x08\xc7\xd9\x8c\xb3\xbfrh\xa9[\xf5\x08\x1be'  # noqa: E501


class WethDecoderBase(DecoderInterface, ABC):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
            base_asset: CryptoAsset,
            wrapped_token: EvmToken,
            counterparty: str,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.base_asset = base_asset
        self.wrapped_token = wrapped_token
        self.counterparty = counterparty

    def _decode_wrapper(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == WETH_DEPOSIT_TOPIC:
            return self._decode_deposit_event(context)

        if context.tx_log.topics[0] == WETH_WITHDRAW_TOPIC:
            return self._decode_withdrawal_event(context)

        return DEFAULT_DECODING_OUTPUT

    def _decode_deposit_event(self, context: DecoderContext) -> DecodingOutput:
        depositor = hex_or_bytes_to_address(context.tx_log.topics[1])
        deposited_amount_raw = hex_or_bytes_to_int(context.tx_log.data[:32])
        deposited_amount = asset_normalized_value(
            amount=deposited_amount_raw,
            asset=self.base_asset,
        )

        out_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.address in (self.wrapped_token.evm_address, depositor) and
                event.balance.amount == deposited_amount and
                event.asset == self.base_asset
            ):
                if event.address == depositor:
                    return DEFAULT_DECODING_OUTPUT

                event.counterparty = self.counterparty
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Wrap {deposited_amount} {self.base_asset.symbol} in {self.wrapped_token.symbol}'  # noqa: E501
                out_event = event

        if out_event is None:
            return DEFAULT_DECODING_OUTPUT

        in_event = self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=self.wrapped_token,
            balance=Balance(amount=deposited_amount),
            location_label=depositor,
            counterparty=self.counterparty,
            notes=f'Receive {deposited_amount} {self.wrapped_token.symbol}',
            address=context.transaction.to_address,
        )
        return DecodingOutput(event=in_event)

    def _decode_withdrawal_event(self, context: DecoderContext) -> DecodingOutput:
        withdrawer = hex_or_bytes_to_address(context.tx_log.topics[1])
        withdrawn_amount_raw = hex_or_bytes_to_int(context.tx_log.data[:32])
        withdrawn_amount = asset_normalized_value(
            amount=withdrawn_amount_raw,
            asset=self.base_asset,
        )

        in_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.address in (self.wrapped_token.evm_address, withdrawer) and
                event.balance.amount == withdrawn_amount and
                event.asset == self.base_asset
            ):
                if event.address == withdrawer:
                    return DEFAULT_DECODING_OUTPUT

                in_event = event
                event.notes = f'Receive {withdrawn_amount} {self.base_asset.symbol}'
                event.counterparty = self.counterparty

        if in_event is None:
            return DEFAULT_DECODING_OUTPUT

        out_event = self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=self.wrapped_token,
            balance=Balance(amount=withdrawn_amount),
            location_label=withdrawer,
            counterparty=self.counterparty,
            notes=f'Unwrap {withdrawn_amount} {self.wrapped_token.symbol}',
            address=context.transaction.to_address,
        )
        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events + [out_event],
        )
        return DecodingOutput(event=out_event)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.wrapped_token.evm_address: (self._decode_wrapper,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_WETH, label='WETH', image='weth.svg'),)
