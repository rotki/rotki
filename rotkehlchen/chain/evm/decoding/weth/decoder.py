from abc import ABC
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import CryptoAsset, EvmToken
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.decoding.weth.constants import CHAIN_ID_TO_WETH_MAPPING, CPT_WETH
from rotkehlchen.constants.assets import A_ETH, A_WETH_SCROLL
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChainID, ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.user_messages import MessagesAggregator


WETH_DEPOSIT_TOPIC = b'\xe1\xff\xfc\xc4\x92=\x04\xb5Y\xf4\xd2\x9a\x8b\xfcl\xda\x04\xeb[\r<F\x07Q\xc2@,\\\\\xc9\x10\x9c'  # noqa: E501
WETH_WITHDRAW_TOPIC = b'\x7f\xcfS,\x15\xf0\xa6\xdb\x0b\xd6\xd0\xe08\xbe\xa7\x1d0\xd8\x08\xc7\xd9\x8c\xb3\xbfrh\xa9[\xf5\x08\x1be'  # noqa: E501
WETH_DEPOSIT_METHOD = b'\xd0\xe3\r\xb0'
WETH_WITHDRAW_METHOD = b'.\x1a}M'


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
        input_data = context.transaction.input_data

        # WETH on Arbitrum is deployed as proxy, we need to check the method
        # On the scroll, the contract is different, So we need to check the method.
        if context.tx_log.topics[0] == WETH_DEPOSIT_TOPIC or (
            self.evm_inquirer.chain_id in {ChainID.ARBITRUM_ONE, ChainID.SCROLL} and
            input_data.startswith(WETH_DEPOSIT_METHOD)
        ):
            return self._decode_deposit_event(context)

        if context.tx_log.topics[0] == WETH_WITHDRAW_TOPIC or (
            self.evm_inquirer.chain_id in {ChainID.ARBITRUM_ONE, ChainID.SCROLL} and
            input_data.startswith(WETH_WITHDRAW_METHOD)
        ):
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

        # This is only for withdrawals on Scroll because the unwrap method on WETH on scroll
        # generates an additional log (Transfer) which doesn't exists on other chains.
        # Because of this additional log this method will be called twice instead of once,
        # therefore we need to skip the second call to avoid creating extra events.
        # Check this for example:
        # A withdraw on Scroll: https://scrollscan.com/tx/0x88f49633073a7667f93eb888ec2151c26f449cc10afca565a15f8df68ee20f82#eventlog
        # A withdraw on Ethereum: https://etherscan.io/tx/0xe5d6fa9c60f595a624e1dd71cb3b28ba9260e90cf3097c5b285b901a97b6246d#eventlog
        if self.evm_inquirer.chain_id == ChainID.SCROLL:
            for event in context.decoded_events:
                if (
                    event.counterparty == CPT_WETH and
                    event.asset == A_WETH_SCROLL and
                    event.balance.amount == withdrawn_amount
                ):
                    return DEFAULT_DECODING_OUTPUT  # we have already decoded this event

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


class WethDecoder(WethDecoderBase):
    """
    Weth Decoder for all supported EVM chains except Gnosis and Polygon Pos
    because of different counterparty and not having ETH as native token.
    """

    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            base_tools: 'BaseDecoderTools',
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
