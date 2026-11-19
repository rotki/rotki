import logging
from typing import TYPE_CHECKING, Any, NamedTuple

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.connext.constants import (
    CANCELLED_TOPICS,
    CONNEXT_CPT_DETAILS,
    CPT_CONNEXT,
    FULFILLED_TOPICS,
    PREPARED_TOPICS,
    TRANSACTION_CANCELLED_TOPIC,
    TRANSACTION_FULFILLED_TOPIC,
    TRANSACTION_PREPARED_TOPIC,
)
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.utils import make_bridge_extra_data, set_bridge_extra_data
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import CryptoAsset
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ConnextTxData(NamedTuple):
    user: ChecksumEvmAddress
    initiator: ChecksumEvmAddress
    sending_asset_id: ChecksumEvmAddress
    receiving_asset_id: ChecksumEvmAddress
    sending_chain_fallback: ChecksumEvmAddress
    receiving_address: ChecksumEvmAddress
    sending_chain_id: int
    receiving_chain_id: int
    amount: int
    relayer_fee: int = 0


def _chain_label(chain_id: int) -> str | None:
    """Return a display label for a chain id known to rotki."""
    try:
        return ChainID.deserialize(chain_id).label()
    except DeserializationError:
        return None


def _parse_tx_data(
        data: bytes,
        offset: int,
        has_initiator: bool,
        include_relayer_fee: bool = False,
) -> ConnextTxData | None:
    """Parse the static TransactionData struct (and optional relayerFee) from an NXTP log."""
    word_count = 16 if has_initiator else 15
    tx_data_size = word_count * 32
    required_end = offset + tx_data_size + (32 if include_relayer_fee else 0)
    if offset < 0 or len(data) < required_end:
        return None

    user = bytes_to_address(data[offset + 32:offset + 64])
    if has_initiator:
        initiator = bytes_to_address(data[offset + 96:offset + 128])
        shift = 32
    else:
        initiator = user
        shift = 0

    relayer_fee = (
        int.from_bytes(data[offset + tx_data_size:offset + tx_data_size + 32])
        if include_relayer_fee else 0
    )
    return ConnextTxData(
        user=user,
        initiator=initiator,
        sending_asset_id=bytes_to_address(data[offset + 96 + shift:offset + 128 + shift]),
        receiving_asset_id=bytes_to_address(data[offset + 128 + shift:offset + 160 + shift]),
        sending_chain_fallback=bytes_to_address(data[offset + 160 + shift:offset + 192 + shift]),
        receiving_address=bytes_to_address(data[offset + 192 + shift:offset + 224 + shift]),
        sending_chain_id=int.from_bytes(data[offset + 320 + shift:offset + 352 + shift]),
        receiving_chain_id=int.from_bytes(data[offset + 352 + shift:offset + 384 + shift]),
        amount=int.from_bytes(data[offset + 384 + shift:offset + 416 + shift]),
        relayer_fee=relayer_fee,
    )


class ConnextDecoder(EvmDecoderInterface):
    """Decoder for Connext NXTP (xPollinate v2 / Connext Bridge) TransactionManager events."""

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
            transaction_managers: tuple[ChecksumEvmAddress, ...],
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.transaction_managers = transaction_managers

    def _resolve_asset(self, asset_id: ChecksumEvmAddress) -> CryptoAsset:
        if asset_id == ZERO_ADDRESS:
            return self.node_inquirer.native_token
        return self.base.get_or_create_evm_token(address=asset_id)

    def _decode_nxtp_event(self, context: DecoderContext) -> EvmDecodingOutput:
        if len(context.tx_log.topics) < 4:
            return DEFAULT_EVM_DECODING_OUTPUT

        topic0 = context.tx_log.topics[0]
        if topic0 in PREPARED_TOPICS:
            tx_data = _parse_tx_data(
                data=context.tx_log.data,
                offset=0,
                has_initiator=topic0 == TRANSACTION_PREPARED_TOPIC,
            )
            if tx_data is None:
                log.warning(
                    'Malformed Connext TransactionPrepared log data in %s tx %s',
                    self.node_inquirer.chain_name,
                    context.transaction.tx_hash,
                )
                return DEFAULT_EVM_DECODING_OUTPUT
            return self._decode_prepared(context=context, tx_data=tx_data)

        if topic0 in FULFILLED_TOPICS:
            is_v01 = topic0 == TRANSACTION_FULFILLED_TOPIC
            if is_v01 and len(context.tx_log.data) < 32:
                log.warning(
                    'Malformed Connext TransactionFulfilled log data in %s tx %s',
                    self.node_inquirer.chain_name,
                    context.transaction.tx_hash,
                )
                return DEFAULT_EVM_DECODING_OUTPUT
            offset = int.from_bytes(context.tx_log.data[0:32]) if is_v01 else 0
            tx_data = _parse_tx_data(
                data=context.tx_log.data,
                offset=offset,
                has_initiator=is_v01,
                include_relayer_fee=True,
            )
            if tx_data is None:
                log.warning(
                    'Malformed Connext TransactionFulfilled log data in %s tx %s',
                    self.node_inquirer.chain_name,
                    context.transaction.tx_hash,
                )
                return DEFAULT_EVM_DECODING_OUTPUT
            return self._decode_fulfilled(context=context, tx_data=tx_data)

        if topic0 in CANCELLED_TOPICS:
            is_v01 = topic0 == TRANSACTION_CANCELLED_TOPIC
            if is_v01 and len(context.tx_log.data) < 32:
                log.warning(
                    'Malformed Connext TransactionCancelled log data in %s tx %s',
                    self.node_inquirer.chain_name,
                    context.transaction.tx_hash,
                )
                return DEFAULT_EVM_DECODING_OUTPUT
            offset = int.from_bytes(context.tx_log.data[0:32]) if is_v01 else 0
            tx_data = _parse_tx_data(
                data=context.tx_log.data,
                offset=offset,
                has_initiator=is_v01,
            )
            if tx_data is None:
                log.warning(
                    'Malformed Connext TransactionCancelled log data in %s tx %s',
                    self.node_inquirer.chain_name,
                    context.transaction.tx_hash,
                )
                return DEFAULT_EVM_DECODING_OUTPUT
            return self._decode_cancelled(context=context, tx_data=tx_data)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_prepared(
            self,
            context: DecoderContext,
            tx_data: ConnextTxData,
    ) -> EvmDecodingOutput:
        """Decode sending-chain TransactionPrepared as a bridge deposit.

        Receiving-chain TransactionPrepared only locks router liquidity inside the contract
        with no user token transfer, so it is ignored.
        """
        if tx_data.sending_chain_id != self.node_inquirer.chain_id.value:
            return DEFAULT_EVM_DECODING_OUTPUT

        tracked_senders = {
            address
            for address in (tx_data.initiator, tx_data.user)
            if self.base.is_tracked(address)
        }
        if len(tracked_senders) == 0:
            return DEFAULT_EVM_DECODING_OUTPUT

        sending_asset = self._resolve_asset(tx_data.sending_asset_id)
        expected_amount = asset_normalized_value(amount=tx_data.amount, asset=sending_asset)
        if (to_chain_label := _chain_label(tx_data.receiving_chain_id)) is not None:
            chain_info = f' from {self.node_inquirer.chain_id.label()} to {to_chain_label}'
        else:
            chain_info = ''

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label in tracked_senders and
                event.counterparty is None and
                event.asset == sending_asset and
                event.amount == expected_amount
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_CONNEXT
                event.notes = (
                    f'Bridge {event.amount} {event.asset.symbol_or_name()}'
                    f'{chain_info} via Connext'
                )
                set_bridge_extra_data(
                    event=event,
                    from_chain=self.node_inquirer.chain_id,
                    to_chain=tx_data.receiving_chain_id,
                    from_address=event.location_label,
                    to_address=tx_data.receiving_address,
                    to_asset=tx_data.receiving_asset_id,
                    transfer_id=context.tx_log.topics[3].hex(),
                )
                break
        else:
            log.error(
                'Could not find matching spend event for %s Connext bridge deposit %s',
                self.node_inquirer.chain_name,
                context.transaction.tx_hash,
            )

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_fulfilled(
            self,
            context: DecoderContext,
            tx_data: ConnextTxData,
    ) -> EvmDecodingOutput:
        """Decode receiving-chain TransactionFulfilled as a bridge withdrawal.

        Sending-chain TransactionFulfilled only credits router liquidity internally
        with no user token transfer, so it is ignored.
        """
        if (
            tx_data.receiving_chain_id != self.node_inquirer.chain_id.value or
            not self.base.is_tracked(tx_data.receiving_address)
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        if (net_raw_amount := tx_data.amount - tx_data.relayer_fee) <= 0:
            return DEFAULT_EVM_DECODING_OUTPUT

        receiving_asset = self._resolve_asset(tx_data.receiving_asset_id)
        expected_amount = asset_normalized_value(amount=net_raw_amount, asset=receiving_asset)
        if (from_chain_label := _chain_label(tx_data.sending_chain_id)) is not None:
            chain_info = f' from {from_chain_label} to {self.node_inquirer.chain_id.label()}'
        else:
            chain_info = ''

        transfer_id = context.tx_log.topics[3].hex()
        bridge_extra_data = make_bridge_extra_data(
            from_chain=tx_data.sending_chain_id,
            to_chain=self.node_inquirer.chain_id,
            from_address=tx_data.user,
            to_address=tx_data.receiving_address,
            transfer_id=transfer_id,
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == tx_data.receiving_address and
                event.counterparty is None and
                event.asset == receiving_asset and
                event.amount == expected_amount
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_CONNEXT
                event.notes = (
                    f'Bridge {event.amount} {event.asset.symbol_or_name()}'
                    f'{chain_info} via Connext'
                )
                set_bridge_extra_data(
                    event=event,
                    from_chain=tx_data.sending_chain_id,
                    to_chain=self.node_inquirer.chain_id,
                    from_address=tx_data.user,
                    to_address=tx_data.receiving_address,
                    transfer_id=transfer_id,
                )
                break
        else:
            return EvmDecodingOutput(action_items=[ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=receiving_asset,
                amount=expected_amount,
                location_label=tx_data.receiving_address,
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.BRIDGE,
                to_counterparty=CPT_CONNEXT,
                to_notes=f'Bridge {{amount}} {{symbol}}{chain_info} via Connext',
                extra_data=bridge_extra_data,
            )])

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_cancelled(
            self,
            context: DecoderContext,
            tx_data: ConnextTxData,
    ) -> EvmDecodingOutput:
        """Decode sending-chain TransactionCancelled as a bridge refund."""
        if (
            tx_data.sending_chain_id != self.node_inquirer.chain_id.value or
            not self.base.is_tracked(tx_data.sending_chain_fallback)
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        sending_asset = self._resolve_asset(tx_data.sending_asset_id)
        expected_amount = asset_normalized_value(amount=tx_data.amount, asset=sending_asset)
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == tx_data.sending_chain_fallback and
                event.counterparty is None and
                event.asset == sending_asset and
                event.amount == expected_amount
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REFUND
                event.counterparty = CPT_CONNEXT
                event.notes = (
                    f'Receive {event.amount} {event.asset.symbol_or_name()} as refund from Connext'
                )
                break
        else:
            return EvmDecodingOutput(action_items=[ActionItem(
                action='transform',
                from_event_type=HistoryEventType.RECEIVE,
                from_event_subtype=HistoryEventSubType.NONE,
                asset=sending_asset,
                amount=expected_amount,
                location_label=tx_data.sending_chain_fallback,
                to_event_type=HistoryEventType.WITHDRAWAL,
                to_event_subtype=HistoryEventSubType.REFUND,
                to_counterparty=CPT_CONNEXT,
                to_notes='Receive {amount} {symbol} as refund from Connext',
            )])

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(self.transaction_managers, (self._decode_nxtp_event,))

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CONNEXT_CPT_DETAILS,)
