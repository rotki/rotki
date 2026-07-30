from typing import TYPE_CHECKING, Any

from eth_abi import decode as decode_abi
from eth_abi.exceptions import DecodingError
from eth_utils import to_checksum_address

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.abi import decode_event_data_abi
from rotkehlchen.chain.evm.constants import ETH_SPECIAL_ADDRESS, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.lifi.constants import (
    CALL_DIAMOND_WITH_EIP2612_SIGNATURE_SELECTOR,
    CALL_DIAMOND_WITH_PERMIT2_SELECTOR,
    CPT_LIFI,
    GENERIC_SWAP_COMPLETED_ABI,
    GENERIC_SWAP_COMPLETED_TOPIC,
    INTENT_REFUNDED_TOPIC,
    LIFI_DIAMOND,
    LIFI_DIAMOND_BASE_RECOVERY,
    LIFI_DIAMOND_ETHEREUM,
    LIFI_DIAMOND_MONAD,
    LIFI_FEE_ROUTER_MONAD,
    LIFI_INTENT_REFUND_BASE,
    MAYAN_ORDER_REFUNDED_TOPIC,
    MAYAN_SWIFT,
    START_BRIDGE_TOKENS_VIA_GLACIS_SELECTOR,
    START_BRIDGE_TOKENS_VIA_RELAY_DEPOSITORY_SELECTOR,
    SWAP_AND_START_BRIDGE_TOKENS_VIA_RELAY_DEPOSITORY_SELECTOR,
    SWAP_AND_START_BRIDGE_TOKENS_VIA_SQUID_SELECTOR,
    SWAPPED_GENERIC_ABI,
    SWAPPED_GENERIC_TOPIC,
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

    @staticmethod
    def _decode_permit2_source_asset(input_data: bytes) -> ChecksumEvmAddress | None:
        if (
            not input_data.startswith(CALL_DIAMOND_WITH_PERMIT2_SELECTOR) or
            len(input_data) < len(CALL_DIAMOND_WITH_PERMIT2_SELECTOR) + 64
        ):
            return None

        token_word_start = len(CALL_DIAMOND_WITH_PERMIT2_SELECTOR) + 32
        return string_to_evm_address(to_checksum_address(
            input_data[token_word_start + 12:token_word_start + 32],
        ))

    @staticmethod
    def _unwrap_diamond_calldata(input_data: bytes) -> bytes:
        if input_data.startswith(CALL_DIAMOND_WITH_PERMIT2_SELECTOR):
            calldata_offset_position = len(CALL_DIAMOND_WITH_PERMIT2_SELECTOR)
        elif input_data.startswith(CALL_DIAMOND_WITH_EIP2612_SIGNATURE_SELECTOR):
            calldata_offset_position = (
                len(CALL_DIAMOND_WITH_EIP2612_SIGNATURE_SELECTOR) + 32 * 6
            )
        else:
            return input_data

        if len(input_data) < calldata_offset_position + 32:
            return b''

        arguments_start = len(CALL_DIAMOND_WITH_PERMIT2_SELECTOR)
        calldata_start = arguments_start + int.from_bytes(
            input_data[calldata_offset_position:calldata_offset_position + 32],
        )
        if len(input_data) < calldata_start + 32:
            return b''

        calldata_length = int.from_bytes(input_data[calldata_start:calldata_start + 32])
        return input_data[calldata_start + 32:calldata_start + 32 + calldata_length]

    @staticmethod
    def _decode_glacis_target_asset(input_data: bytes) -> ChecksumEvmAddress | None:
        input_data = LifiDecoder._unwrap_diamond_calldata(input_data)

        if not input_data.startswith(START_BRIDGE_TOKENS_VIA_GLACIS_SELECTOR):
            return None

        try:
            _, glacis_data = decode_abi(
                types=[
                    '(bytes32,string,string,address,address,address,uint256,uint256,bool,bool)',
                    '(bytes32,address,uint256,bytes32)',
                ],
                data=input_data[len(START_BRIDGE_TOKENS_VIA_GLACIS_SELECTOR):],
            )
        except DecodingError:
            return None

        if any((output_token := glacis_data[3])[:12]):
            return None  # bytes32 output tokens for non-EVM destinations are not addresses

        return string_to_evm_address(to_checksum_address(output_token[-20:]))

    @staticmethod
    def _decode_relay_depository_order_id(input_data: bytes) -> str | None:
        """Read Relay's order id from the LI.FI facet calldata.

        RelayDepositoryData is the final static tuple argument. Its order id is the
        second head word for a direct bridge and the third for a swap-and-bridge.
        """
        input_data = LifiDecoder._unwrap_diamond_calldata(input_data)
        if input_data.startswith(START_BRIDGE_TOKENS_VIA_RELAY_DEPOSITORY_SELECTOR):
            order_id_start = len(START_BRIDGE_TOKENS_VIA_RELAY_DEPOSITORY_SELECTOR) + 32
        elif input_data.startswith(SWAP_AND_START_BRIDGE_TOKENS_VIA_RELAY_DEPOSITORY_SELECTOR):
            order_id_start = (
                len(SWAP_AND_START_BRIDGE_TOKENS_VIA_RELAY_DEPOSITORY_SELECTOR) + 64
            )
        else:
            return None

        if len(input_data) < order_id_start + 32:
            return None
        return input_data[order_id_start:order_id_start + 32].hex()

    @staticmethod
    def _decode_squid_assets(
            input_data: bytes,
            receiver: ChecksumEvmAddress,
    ) -> tuple[ChecksumEvmAddress | None, ChecksumEvmAddress | None]:
        input_data = LifiDecoder._unwrap_diamond_calldata(input_data)
        if not input_data.startswith(SWAP_AND_START_BRIDGE_TOKENS_VIA_SQUID_SELECTOR):
            return None, None

        try:
            _, swap_data, squid_data = decode_abi(
                types=[
                    '(bytes32,string,string,address,address,address,uint256,uint256,bool,bool)',
                    '(address,address,address,address,uint256,bytes,bool)[]',
                    '(uint8,string,string,string,address,(uint8,address,uint256,bytes,bytes)[],bytes,uint256,bool)',
                ],
                data=input_data[len(SWAP_AND_START_BRIDGE_TOKENS_VIA_SQUID_SELECTOR):],
            )
            destination_calls, _ = decode_abi(
                types=['(uint8,address,uint256,bytes,bytes)[]', 'address'],
                data=squid_data[6],
            )
        except DecodingError:
            return None, None

        if len(swap_data) == 0:
            return None, None

        source_asset = string_to_evm_address(to_checksum_address(swap_data[0][2]))
        for call_type, target, _, call_data, payload in reversed(destination_calls):
            if to_checksum_address(target) != receiver or len(call_data) != 0:
                continue
            if call_type == 2:  # FullNativeBalance
                return ZERO_ADDRESS, source_asset
            if call_type == 1 and len(payload) >= 32:  # FullTokenBalance
                return string_to_evm_address(to_checksum_address(payload[12:32])), source_asset

        return None, source_asset

    def _decode_lifi(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] in (GENERIC_SWAP_COMPLETED_TOPIC, SWAPPED_GENERIC_TOPIC):
            return self._decode_swap(context)
        if context.tx_log.topics[0] in (TRANSFER_COMPLETED_TOPIC, TRANSFER_RECOVERED_TOPIC):
            return self._decode_completed(context)
        if context.tx_log.topics[0] in (INTENT_REFUNDED_TOPIC, MAYAN_ORDER_REFUNDED_TOPIC):
            return self._decode_refund(context)
        return self._decode_started(context)

    def _decode_swap(self, context: DecoderContext) -> EvmDecodingOutput:
        _, data = decode_event_data_abi(
            context.tx_log,
            GENERIC_SWAP_COMPLETED_ABI
            if context.tx_log.topics[0] == GENERIC_SWAP_COMPLETED_TOPIC
            else SWAPPED_GENERIC_ABI,
        )
        if context.tx_log.topics[0] == GENERIC_SWAP_COMPLETED_TOPIC:
            receiver, from_asset_address, to_asset_address = data[2:5]
            from_amount_raw, to_amount_raw = data[5:7]
        else:
            receiver = None  # The deprecated event did not include the receiver
            from_asset_address, to_asset_address = data[2:4]
            from_amount_raw, to_amount_raw = data[4:6]

        from_asset = (
            self.node_inquirer.native_token
            if from_asset_address in (ZERO_ADDRESS, ETH_SPECIAL_ADDRESS)
            else self.base.get_or_create_evm_token(address=from_asset_address)
        )
        to_asset = (
            self.node_inquirer.native_token
            if to_asset_address in (ZERO_ADDRESS, ETH_SPECIAL_ADDRESS)
            else self.base.get_or_create_evm_token(address=to_asset_address)
        )
        from_amount = asset_normalized_value(amount=int(from_amount_raw), asset=from_asset)
        to_amount = asset_normalized_value(amount=int(to_amount_raw), asset=to_asset)
        spend_event = receive_event = None
        for event in context.decoded_events:
            if (
                event.location_label == context.transaction.from_address and
                event.asset == from_asset and
                event.amount == from_amount and
                (event.event_type, event.event_subtype) in (
                    (HistoryEventType.SPEND, HistoryEventSubType.NONE),
                    (HistoryEventType.TRADE, HistoryEventSubType.SPEND),
                )
            ):
                spend_event = event
            elif (
                (receiver is None or event.location_label == receiver) and
                event.asset == to_asset and
                event.amount == to_amount and
                (event.event_type, event.event_subtype) in (
                    (HistoryEventType.RECEIVE, HistoryEventSubType.NONE),
                    (HistoryEventType.TRADE, HistoryEventSubType.RECEIVE),
                )
            ):
                receive_event = event

        if spend_event is None or receive_event is None:
            return DEFAULT_EVM_DECODING_OUTPUT

        spend_event.event_type = receive_event.event_type = HistoryEventType.TRADE
        spend_event.event_subtype = HistoryEventSubType.SPEND
        receive_event.event_subtype = HistoryEventSubType.RECEIVE
        spend_event.counterparty = CPT_LIFI
        spend_event.notes = (
            f'Swap {spend_event.amount} {spend_event.asset.symbol_or_name()} via LI.FI'
        )
        receive_event.notes = (
            f'Receive {receive_event.amount} {receive_event.asset.symbol_or_name()} '
            'as the result of a swap via LI.FI'
        )
        maybe_reshuffle_events(
            ordered_events=[spend_event, receive_event],
            events_list=context.decoded_events,
        )
        return EvmDecodingOutput(process_swaps=True)

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
            source_asset = self._decode_permit2_source_asset(context.transaction.input_data)
            receiving_asset = self._decode_glacis_target_asset(context.transaction.input_data)
            if receiving_asset is None:
                receiving_asset, squid_source_asset = self._decode_squid_assets(
                    input_data=context.transaction.input_data,
                    receiver=receiver,
                )
                source_asset = source_asset or squid_source_asset
            amount = int(bridge_data[6])
            destination_chain = int(bridge_data[7])
            transfer_id = (
                self._decode_relay_depository_order_id(context.transaction.input_data) or
                bridge_data[0].hex()
            )
        else:
            sending_asset = data[4]
            receiving_asset = data[5]
            source_asset = None
            receiver = data[6]
            amount = int(data[7])
            destination_chain = int(data[8])
            transfer_id = context.tx_log.topics[1].hex()
        sender = context.transaction.from_address
        if sending_asset in (ZERO_ADDRESS, ETH_SPECIAL_ADDRESS):
            expected_asset = self.node_inquirer.native_token
        else:
            expected_asset = self.base.get_or_create_evm_token(address=sending_asset)
        expected_source_asset = (
            self.base.get_or_create_evm_token(address=source_asset)
            if source_asset is not None and source_asset != sending_asset
            else None
        )
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
                (
                    (
                        event.asset == expected_source_asset and
                        event.address == context.transaction.to_address
                    ) or
                    (
                        event.asset == expected_asset and
                        event.amount >= asset_normalized_value(amount, expected_asset)
                    )
                )
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
                    to_asset=receiving_asset,
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
