from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
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
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.user_messages import MessagesAggregator

WETH_CONTRACT = string_to_evm_address('0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2')
WETH_DEPOSIT_TOPIC = b'\xe1\xff\xfc\xc4\x92=\x04\xb5Y\xf4\xd2\x9a\x8b\xfcl\xda\x04\xeb[\r<F\x07Q\xc2@,\\\\\xc9\x10\x9c'  # noqa: E501
WETH_WITHDRAW_TOPIC = b'\x7f\xcfS,\x15\xf0\xa6\xdb\x0b\xd6\xd0\xe08\xbe\xa7\x1d0\xd8\x08\xc7\xd9\x8c\xb3\xbfrh\xa9[\xf5\x08\x1be'  # noqa: E501


class WethDecoder(DecoderInterface):
    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=ethereum_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.weth = A_WETH.resolve_to_evm_token()
        self.eth = A_ETH.resolve_to_crypto_asset()

    def _decode_weth(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == WETH_DEPOSIT_TOPIC:
            return self._decode_deposit_event(context)

        if context.tx_log.topics[0] == WETH_WITHDRAW_TOPIC:
            return self._decode_withdrawal_event(context)

        return DEFAULT_DECODING_OUTPUT

    def _decode_deposit_event(self, context: DecoderContext) -> DecodingOutput:
        depositor = hex_or_bytes_to_address(context.tx_log.topics[1])
        deposited_amount_raw = hex_or_bytes_to_int(context.tx_log.data[:32])
        deposited_amount = asset_normalized_value(amount=deposited_amount_raw, asset=self.eth)

        out_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.address in (WETH_CONTRACT, depositor) and
                event.balance.amount == deposited_amount and
                event.asset == self.eth
            ):
                if event.address == depositor:
                    return DEFAULT_DECODING_OUTPUT

                event.counterparty = CPT_WETH
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Wrap {deposited_amount} {self.eth.symbol} in {self.weth.symbol}'
                out_event = event

        if out_event is None:
            return DEFAULT_DECODING_OUTPUT

        in_event = self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=self.weth,
            balance=Balance(amount=deposited_amount),
            location_label=depositor,
            counterparty=CPT_WETH,
            notes=f'Receive {deposited_amount} {self.weth.symbol}',
            address=context.transaction.to_address,
        )
        return DecodingOutput(event=in_event)

    def _decode_withdrawal_event(self, context: DecoderContext) -> DecodingOutput:
        withdrawer = hex_or_bytes_to_address(context.tx_log.topics[1])
        withdrawn_amount_raw = hex_or_bytes_to_int(context.tx_log.data[:32])
        withdrawn_amount = asset_normalized_value(amount=withdrawn_amount_raw, asset=self.eth)

        in_event = None
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.address in (WETH_CONTRACT, withdrawer) and
                event.balance.amount == withdrawn_amount and
                event.asset == self.eth
            ):
                if event.address == withdrawer:
                    return DEFAULT_DECODING_OUTPUT

                in_event = event
                event.notes = f'Receive {withdrawn_amount} {self.eth.symbol}'
                event.counterparty = CPT_WETH

        if in_event is None:
            return DEFAULT_DECODING_OUTPUT

        out_event = self.base.make_event_next_index(
            tx_hash=context.transaction.tx_hash,
            timestamp=context.transaction.timestamp,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=self.weth,
            balance=Balance(amount=withdrawn_amount),
            location_label=withdrawer,
            counterparty=CPT_WETH,
            notes=f'Unwrap {withdrawn_amount} {self.weth.symbol}',
            address=context.transaction.to_address,
        )
        maybe_reshuffle_events(
            ordered_events=[out_event, in_event],
            events_list=context.decoded_events + [out_event],
        )
        return DecodingOutput(event=out_event)

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            WETH_CONTRACT: (self._decode_weth,),
        }

    def counterparties(self) -> list[CounterpartyDetails]:
        return [CounterpartyDetails(identifier=CPT_WETH, label='WETH', image='weth.svg')]
