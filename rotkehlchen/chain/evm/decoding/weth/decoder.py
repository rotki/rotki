import logging
from abc import ABC
from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import DEPOSIT_TOPIC_V2
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.decoding.weth.constants import CHAIN_ID_TO_WETH_MAPPING, CPT_WETH
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


WETH_WITHDRAW_TOPIC: Final = b'\x7f\xcfS,\x15\xf0\xa6\xdb\x0b\xd6\xd0\xe08\xbe\xa7\x1d0\xd8\x08\xc7\xd9\x8c\xb3\xbfrh\xa9[\xf5\x08\x1be'  # noqa: E501

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class WethDecoderBase(EvmDecoderInterface, ABC):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
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

    def _decode_wrapper(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] == DEPOSIT_TOPIC_V2:
            return self._decode_deposit_event(context)
        elif context.tx_log.topics[0] == WETH_WITHDRAW_TOPIC:
            return self._decode_withdrawal_event(context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_deposit_event(self, context: DecoderContext) -> EvmDecodingOutput:
        deposited_amount_raw = int.from_bytes(context.tx_log.data[:32])
        deposited_amount = asset_normalized_value(
            amount=deposited_amount_raw,
            asset=self.base_asset,
        )

        out_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.address == self.wrapped_token.evm_address and
                event.amount == deposited_amount and
                event.asset == self.base_asset
            ):
                event.counterparty = self.counterparty
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Wrap {deposited_amount} {self.base_asset.symbol} in {self.wrapped_token.symbol}'  # noqa: E501
                out_event = event

        if out_event is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        in_event = self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=self.wrapped_token,
            amount=deposited_amount,
            location_label=out_event.location_label,
            counterparty=self.counterparty,
            notes=f'Receive {deposited_amount} {self.wrapped_token.symbol}',
            address=context.transaction.to_address,
        )
        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events + [in_event],
        )
        return EvmDecodingOutput(events=[in_event])

    def _decode_withdrawal_event(self, context: DecoderContext) -> EvmDecodingOutput:
        if not self.base.is_tracked(withdrawer := bytes_to_address(context.tx_log.topics[1])):
            return DEFAULT_EVM_DECODING_OUTPUT

        withdrawn_amount_raw = int.from_bytes(context.tx_log.data[:32])
        withdrawn_amount = asset_normalized_value(
            amount=withdrawn_amount_raw,
            asset=self.base_asset,
        )
        in_event = out_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.address == self.wrapped_token.evm_address and
                event.amount == withdrawn_amount and
                event.asset == self.base_asset
            ):
                in_event = event
                event.notes = f'Receive {withdrawn_amount} {self.base_asset.symbol}'
                event.counterparty = self.counterparty

        if in_event is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        out_event = self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=self.wrapped_token,
            amount=withdrawn_amount,
            location_label=withdrawer,
            counterparty=self.counterparty,
            notes=f'Unwrap {withdrawn_amount} {self.wrapped_token.symbol}',
            address=context.transaction.to_address,
        )
        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events + [out_event],
        )
        return EvmDecodingOutput(events=[out_event])

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {self.wrapped_token.evm_address: (self._decode_wrapper,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_WETH, label='WETH', image='weth.svg'),)


class WethDecoder(WethDecoderBase):
    """
    Weth Decoder for EVM chains except Gnosis and Polygon Pos
    because of different counterparty and not having ETH as native token.
    Arbitrum One and Scroll are based on this decoder but have some special
    logic since their contracts don't follow the weth9 implementation.
    """

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseEvmDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            base_asset=A_ETH.resolve_to_crypto_asset(),
            wrapped_token=CHAIN_ID_TO_WETH_MAPPING[evm_inquirer.chain_id].resolve_to_evm_token(),
            counterparty=CPT_WETH,
        )
