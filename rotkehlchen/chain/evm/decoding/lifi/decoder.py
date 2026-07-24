from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.lifi.constants import (
    CPT_LIFI,
    INTENT_REFUNDED_TOPIC,
    LIFI_DIAMOND,
    LIFI_DIAMOND_BASE_RECOVERY,
    LIFI_DIAMOND_ETHEREUM,
    LIFI_DIAMOND_MONAD,
    LIFI_FEE_ROUTER_MONAD,
    LIFI_INTENT_REFUND_BASE,
    MAYAN_ORDER_REFUNDED_TOPIC,
    MAYAN_SWIFT,
    TRANSFER_COMPLETED_ABI,
    TRANSFER_COMPLETED_TOPIC,
    TRANSFER_RECOVERED_ABI,
    TRANSFER_RECOVERED_TOPIC,
    TRANSFER_STARTED_ABI,
    TRANSFER_STARTED_TOPIC,
    TRANSFER_STARTED_TUPLE_ABI,
    TRANSFER_STARTED_TUPLE_TOPIC,
)
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import make_bridge_extra_data, set_bridge_extra_data
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChainID, ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset


class LifiDecoder(EvmDecoderInterface):

    def _decode_lifi(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] in (TRANSFER_COMPLETED_TOPIC, TRANSFER_RECOVERED_TOPIC):
            return self._decode_completed(context)
        if context.tx_log.topics[0] in (INTENT_REFUNDED_TOPIC, MAYAN_ORDER_REFUNDED_TOPIC):
            return self._decode_refund(context)
        return self._decode_started(context)

    def _chain_label(self, chain_id: int) -> str:
        try:
            return ChainID.deserialize_from_db(chain_id).label()
        except DeserializationError:
            return str(chain_id)

    def _decode_started(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] not in (TRANSFER_STARTED_TOPIC, TRANSFER_STARTED_TUPLE_TOPIC):
            return DEFAULT_EVM_DECODING_OUTPUT

        _, data = decode_event_data_abi(
            context.tx_log,
            TRANSFER_STARTED_TUPLE_ABI
            if context.tx_log.topics[0] == TRANSFER_STARTED_TUPLE_TOPIC
            else TRANSFER_STARTED_ABI,
        )
        if context.tx_log.topics[0] == TRANSFER_STARTED_TUPLE_TOPIC:
            bridge_data = data[0]
            sending_asset = bridge_data[4]
            receiver = bridge_data[5]
            amount = int(bridge_data[6])
            destination_chain = int(bridge_data[7])
            transfer_id = bridge_data[0].hex()
        else:
            sending_asset = data[4]
            receiver = data[6]
            amount = int(data[7])
            destination_chain = int(data[8])
            transfer_id = context.tx_log.topics[1].hex()
        sender = context.transaction.from_address
        if sending_asset in (ZERO_ADDRESS, ETH_SPECIAL_ADDRESS):
            expected_asset = self.node_inquirer.native_token
        else:
            expected_asset = self.base.get_or_create_evm_token(address=sending_asset)
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == sender and
                event.counterparty is None and
                event.asset == self.node_inquirer.native_token and
                event.asset != expected_asset and
                event.address == LIFI_FEE_ROUTER_MONAD
            ):
                event.event_subtype = HistoryEventSubType.FEE
                event.counterparty = CPT_LIFI
                event.notes = (
                    f'Spend {event.amount} {event.asset.symbol_or_name()} as a LI.FI bridge fee'
                )

            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == sender and
                event.counterparty is None and
                event.asset == expected_asset and
                event.amount >= asset_normalized_value(amount, expected_asset)
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_LIFI
                event.notes = (
                    f'Bridge {event.amount} {event.asset.symbol_or_name()} from '
                    f'{self.node_inquirer.chain_id.label()} to '
                    f'{self._chain_label(destination_chain)} via LI.FI'
                )
                set_bridge_extra_data(
                    event=event,
                    from_chain=self.node_inquirer.chain_id,
                    to_chain=destination_chain,
                    from_address=sender,
                    to_address=receiver,
                    transfer_id=transfer_id,
                )
                break

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_completed(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] not in (TRANSFER_COMPLETED_TOPIC, TRANSFER_RECOVERED_TOPIC):
            return DEFAULT_EVM_DECODING_OUTPUT

        _, data = decode_event_data_abi(
            context.tx_log,
            TRANSFER_RECOVERED_ABI
            if context.tx_log.topics[0] == TRANSFER_RECOVERED_TOPIC
            else TRANSFER_COMPLETED_ABI,
        )
        receiving_asset = data[0]
        receiver = data[1]
        if not self.base.is_tracked(receiver):
            return DEFAULT_EVM_DECODING_OUTPUT

        expected_asset: Asset
        if receiving_asset in (ZERO_ADDRESS, ETH_SPECIAL_ADDRESS):
            expected_asset = self.node_inquirer.native_token
        else:
            expected_asset = self.base.get_or_create_evm_token(address=receiving_asset)
        expected_amount = asset_normalized_value(amount=int(data[2]), asset=expected_asset)
        bridge_data = make_bridge_extra_data(
            from_chain=None,
            to_chain=self.node_inquirer.chain_id,
            to_address=receiver,
            transfer_id=context.tx_log.topics[1].hex(),
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == receiver and
                event.counterparty is None and
                event.asset == expected_asset
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_LIFI
                event.notes = (
                    f'Bridge {event.amount} {event.asset.symbol_or_name()} to '
                    f'{receiver} at {self.node_inquirer.chain_id.label()} via LI.FI'
                )
                event.extra_data = (event.extra_data or {}) | bridge_data
                break
        else:
            return EvmDecodingOutput(action_items=[ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=expected_asset,
                amount=expected_amount,
                location_label=receiver,
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.BRIDGE,
                to_counterparty=CPT_LIFI,
                to_notes='Bridge {amount} {symbol} to ' + receiver + ' via LI.FI',
                extra_data=bridge_data,
            )])

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_refund(self, context: DecoderContext) -> EvmDecodingOutput:
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label is not None and
                self.base.is_tracked(string_to_evm_address(event.location_label)) and
                event.counterparty is None
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REFUND
                event.counterparty = CPT_LIFI
                event.notes = (
                    f'Receive {event.amount} {event.asset.symbol_or_name()} as refund from LI.FI'
                )
                break

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        addresses = {
            LIFI_DIAMOND: (self._decode_lifi,),
            MAYAN_SWIFT: (self._decode_lifi,),
        }
        if self.node_inquirer.chain_id == ChainID.MONAD:
            addresses[LIFI_DIAMOND_MONAD] = (self._decode_lifi,)
        elif self.node_inquirer.chain_id == ChainID.ETHEREUM:
            addresses[LIFI_DIAMOND_ETHEREUM] = (self._decode_lifi,)
        elif self.node_inquirer.chain_id == ChainID.BASE:
            addresses[LIFI_DIAMOND_BASE_RECOVERY] = (self._decode_lifi,)
            addresses[LIFI_INTENT_REFUND_BASE] = (self._decode_lifi,)
        return addresses

    def decoding_by_input_data(self) -> dict[bytes, dict[bytes, Any]]:
        return {b'\xfe\xea\x83\xf1': {MAYAN_ORDER_REFUNDED_TOPIC: self._decode_lifi}}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_LIFI, label='LI.FI', image='lifi.svg'),)
