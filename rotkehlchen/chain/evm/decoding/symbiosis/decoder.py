import logging
from typing import TYPE_CHECKING, Any, Final

from eth_abi import decode as decode_abi
from eth_abi.exceptions import DecodingError
from eth_utils import to_checksum_address

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.bitcoin.utils import scriptpubkey_to_btc_address
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    ActionItem,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.chain.evm.decoding.symbiosis.constants import (
    BTC_SYNTHESIZE_COMPLETED_TOPIC,
    BURN_COMPLETED_TOPIC,
    BURN_REQUEST_BTC_TOPIC,
    BURN_REQUEST_TON_TOPIC,
    BURN_REQUEST_TOPIC,
    BURN_SYNTHETIC_TOKEN_BTC_SELECTOR,
    BURN_SYNTHETIC_TOKEN_SELECTOR,
    BURN_SYNTHETIC_TOKEN_TON_SELECTOR,
    CPT_SYMBIOSIS,
    META_BURN_SYNTHETIC_TOKEN_SELECTOR,
    META_MINT_SYNTHETIC_TOKEN_SELECTOR,
    ORACLE_REQUEST_TOPIC,
    REVERT_BURN_COMPLETED_TOPIC,
    REVERT_SYNTHESIZE_COMPLETED_TOPIC,
    SYMBIOSIS_BCH_CHAIN_ID,
    SYMBIOSIS_BTC_CHAIN_ID,
    SYMBIOSIS_CPT_DETAILS,
    SYMBIOSIS_DOGE_CHAIN_ID,
    SYMBIOSIS_EXTERNAL_CHAIN_NAMES,
    SYMBIOSIS_SCHAIN_IDS,
    SYMBIOSIS_SOLANA_CHAIN_ID,
    SYNTHESIZE_COMPLETED_TOPIC,
    SYNTHESIZE_REQUEST_TOPIC,
    SymbiosisDeployment,
)
from rotkehlchen.chain.evm.decoding.utils import make_bridge_extra_data, set_bridge_extra_data
from rotkehlchen.chain.evm.decoding.weth.constants import CHAIN_ID_TO_WETH_MAPPING
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.serialization import DeserializationError, EncodingError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, SupportedBlockchain
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from collections.abc import Callable

    from rotkehlchen.assets.asset import CryptoAsset
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.base import BaseEvmDecoderTools
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

META_MINT_ABI_TYPE: Final = (
    '(uint256,uint256,bytes32,bytes32,address,uint256,address,'
    'address[],address,bytes,address,bytes,uint256)'
)
META_BURN_ABI_TYPE: Final = (
    '(uint256,uint256,bytes32,address,address,address,bytes,'
    'uint256,address,address,address,address,uint256,bytes32)'
)
ORACLE_REQUEST_ABI_TYPES: Final = ['address', 'bytes', 'address', 'address', 'uint256']
BURN_SYNTHETIC_ABI_TYPES: Final = [
    'uint256', 'address', 'uint256', 'address',
    'address', 'address', 'address', 'uint256', 'bytes32',
]
BURN_SYNTHETIC_BTC_ABI_TYPES: Final = ['uint256', 'uint256', 'bytes', 'address', 'bytes32']
BURN_SYNTHETIC_TON_ABI_TYPES: Final = [
    'uint256', 'address', 'uint256', 'bytes32', '(int8,bytes32)',
    'address', 'address', 'address', 'uint256', 'bytes32',
]

SYMBIOSIS_TO_ROTKI_NON_EVM_CHAINS: Final[dict[int, str]] = {
    SYMBIOSIS_BTC_CHAIN_ID: SupportedBlockchain.BITCOIN.serialize(),
    SYMBIOSIS_BCH_CHAIN_ID: SupportedBlockchain.BITCOIN_CASH.serialize(),
    SYMBIOSIS_DOGE_CHAIN_ID: SupportedBlockchain.DOGECOIN.serialize(),
    SYMBIOSIS_SOLANA_CHAIN_ID: SupportedBlockchain.SOLANA.serialize(),
}


def _chain_label(chain_id: int) -> str | None:
    """Return a display label for a Symbiosis numeric chain ID."""
    try:
        return ChainID.deserialize(chain_id).label()
    except DeserializationError:
        return SYMBIOSIS_EXTERNAL_CHAIN_NAMES.get(chain_id)


def _serialize_chain(chain_id: int) -> int | str:
    """Use rotki's serialized identifier for non-EVM chains in bridge metadata."""
    return SYMBIOSIS_TO_ROTKI_NON_EVM_CHAINS.get(chain_id, chain_id)


def _decode_btc_recipient(scriptpubkey: bytes) -> str | None:
    """Decode a Bitcoin scriptPubKey into a BTC address, returning None if invalid."""
    try:
        return scriptpubkey_to_btc_address(scriptpubkey)
    except (EncodingError, IndexError) as e:
        log.warning('Failed to decode Symbiosis BTC recipient scriptPubKey: %s', e)
        return None


def _resolve_transfer_id(cross_chain_id: bytes, external_id: bytes) -> str:
    """Return crossChainID when non-zero, falling back to externalID for legacy flows."""
    return cross_chain_id.hex() if any(cross_chain_id) else external_id.hex()


def _parse_final_calldata(final_calldata: bytes) -> tuple[int, str | None] | None:
    """Extract (chain_id, recipient) from nested metaMintSyntheticToken.finalCalldata."""
    if final_calldata.startswith(META_BURN_SYNTHETIC_TOKEN_SELECTOR):
        (meta_burn,) = decode_abi(types=[META_BURN_ABI_TYPE], data=final_calldata[4:])
        return int(meta_burn[12]), to_checksum_address(meta_burn[8])
    if final_calldata.startswith(BURN_SYNTHETIC_TOKEN_SELECTOR):
        args = decode_abi(types=BURN_SYNTHETIC_ABI_TYPES, data=final_calldata[4:])
        return int(args[7]), to_checksum_address(args[3])
    if final_calldata.startswith(BURN_SYNTHETIC_TOKEN_BTC_SELECTOR):
        args = decode_abi(types=BURN_SYNTHETIC_BTC_ABI_TYPES, data=final_calldata[4:])
        return SYMBIOSIS_BTC_CHAIN_ID, _decode_btc_recipient(args[2])
    if final_calldata.startswith(BURN_SYNTHETIC_TOKEN_TON_SELECTOR):
        args = decode_abi(types=BURN_SYNTHETIC_TON_ABI_TYPES, data=final_calldata[4:])
        return int(args[8]), None
    return None


class SymbiosisDecoder(EvmDecoderInterface):
    """Decoder for Symbiosis Finance cross-chain bridge transactions."""

    def __init__(
            self,
            evm_inquirer: EvmNodeInquirer,
            base_tools: BaseEvmDecoderTools,
            msg_aggregator: MessagesAggregator,
            deployment: SymbiosisDeployment,
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )
        self.portal = deployment.portal
        self.synthesis = deployment.synthesis
        self.bridge = deployment.bridge

    def _resolve_final_destination(
            self,
            all_logs: list[EvmTxReceiptLog],
            request_id: bytes,
            hop_chain_id: int,
            default_recipient: ChecksumEvmAddress,
    ) -> tuple[int, str | None]:
        """Resolve final destination chain and recipient for a Portal SynthesizeRequest.

        Modern Symbiosis cross-chain routes pass through the Symbiosis sChain manager
        (chain ID 13863860 or legacy 56288), so ``SynthesizeRequest.chainID`` is the
        intermediate sChain. The actual target chain and recipient live in the paired
        ``BridgeV2.OracleRequest`` calldata (``metaMintSyntheticToken.finalCalldata``).
        """
        if hop_chain_id not in SYMBIOSIS_SCHAIN_IDS:
            return hop_chain_id, default_recipient

        for tx_log in all_logs:
            if (
                tx_log.address != self.bridge or
                len(tx_log.topics) == 0 or
                tx_log.topics[0] != ORACLE_REQUEST_TOPIC
            ):
                continue

            try:
                _, call_data, _, _, _ = decode_abi(
                    types=ORACLE_REQUEST_ABI_TYPES,
                    data=tx_log.data,
                )
                if not call_data.startswith(META_MINT_SYNTHETIC_TOKEN_SELECTOR):
                    continue
                (meta_mint,) = decode_abi(types=[META_MINT_ABI_TYPE], data=call_data[4:])
                if meta_mint[2] != request_id:
                    continue
                if (resolved := _parse_final_calldata(meta_mint[11])) is not None:
                    return resolved
                break
            except DecodingError as e:
                # Ignore OracleRequest logs whose payload differs from metaMintSyntheticToken
                log.debug('Failed to decode Symbiosis OracleRequest log: %s', e)
                continue

        return hop_chain_id, default_recipient

    def _has_synthesis_log(
            self,
            all_logs: list[EvmTxReceiptLog],
            topic0: bytes,
            external_id: bytes,
    ) -> bool:
        """Check whether all_logs contains a Synthesis log with matching topic0 and external_id."""
        return any(
            tx_log.address == self.synthesis and
            len(tx_log.topics) >= 2 and
            tx_log.topics[0] == topic0 and
            tx_log.topics[1] == external_id
            for tx_log in all_logs
        )

    def _resolve_expected_assets(
            self,
            token_addr: ChecksumEvmAddress,
    ) -> tuple[CryptoAsset, tuple[CryptoAsset, ...]]:
        """Resolve an EVM token address plus native token if it is the chain's wrapped native."""
        token = self.base.get_or_create_evm_token(address=token_addr)
        if token == CHAIN_ID_TO_WETH_MAPPING.get(self.node_inquirer.chain_id):
            return token, (self.node_inquirer.native_token, token)
        return token, (token,)

    def _find_bridge_event(
            self,
            decoded_events: list[EvmEvent],
            is_send: bool,
            label_matches: Callable[[str | None], bool],
            expected_token_addr: ChecksumEvmAddress | None,
            expected_raw_amount: int | None,
    ) -> EvmEvent | None:
        """Locate the plain transfer or unpaired DEX swap leg corresponding to a bridge action."""
        plain_type = HistoryEventType.SPEND if is_send else HistoryEventType.RECEIVE
        target_trade_subtype = (
            HistoryEventSubType.SPEND if is_send else HistoryEventSubType.RECEIVE
        )
        opposite_trade_subtype = (
            HistoryEventSubType.RECEIVE if is_send else HistoryEventSubType.SPEND
        )

        candidates = [
            event
            for event in decoded_events
            if (
                event.event_type == plain_type and
                event.event_subtype == HistoryEventSubType.NONE and
                label_matches(event.location_label) and
                event.counterparty is None
            )
        ]
        if len(candidates) == 0:
            paired_trade_labels = {
                event.location_label
                for event in decoded_events
                if (
                    event.event_type == HistoryEventType.TRADE and
                    event.event_subtype == opposite_trade_subtype
                )
            }
            candidates = [
                event
                for event in decoded_events
                if (
                    event.event_type == HistoryEventType.TRADE and
                    event.event_subtype == target_trade_subtype and
                    label_matches(event.location_label) and
                    event.location_label not in paired_trade_labels
                )
            ]

        if len(candidates) == 0:
            return None

        if (
            expected_token_addr is not None and
            expected_token_addr != ZERO_ADDRESS and
            expected_raw_amount is not None
        ):
            expected_token, expected_assets = self._resolve_expected_assets(expected_token_addr)
            expected_amount = asset_normalized_value(
                amount=expected_raw_amount,
                asset=expected_token,
            )
            for candidate in candidates:
                if candidate.asset in expected_assets and candidate.amount == expected_amount:
                    return candidate

        return candidates[0]

    def _decode_bridge_send(
            self,
            context: DecoderContext,
            event_from: ChecksumEvmAddress,
            dest_chain: int,
            dest_recipient: str | None,
            transfer_id: str | None,
            expected_token_addr: ChecksumEvmAddress | None,
            expected_raw_amount: int | None,
    ) -> EvmDecodingOutput:
        """Convert the user's outgoing spend event into a Symbiosis DEPOSIT/BRIDGE event."""
        tracked_senders = {
            address
            for address in {event_from, context.transaction.from_address}
            if self.base.is_tracked(address)
        }
        if len(tracked_senders) == 0:
            return DEFAULT_EVM_DECODING_OUTPUT

        matched_event = self._find_bridge_event(
            decoded_events=context.decoded_events,
            is_send=True,
            label_matches=lambda label: label in tracked_senders,
            expected_token_addr=expected_token_addr,
            expected_raw_amount=expected_raw_amount,
        )
        if matched_event is None:
            log.error(
                'Could not find matching spend event for %s Symbiosis bridge send %s',
                self.node_inquirer.chain_name,
                context.transaction.tx_hash,
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        if (to_chain_label := _chain_label(dest_chain)) is not None:
            chain_info = f' from {self.node_inquirer.chain_id.label()} to {to_chain_label}'
        else:
            chain_info = ''

        matched_event.event_type = HistoryEventType.DEPOSIT
        matched_event.event_subtype = HistoryEventSubType.BRIDGE
        matched_event.counterparty = CPT_SYMBIOSIS
        matched_event.notes = (
            f'Bridge {matched_event.amount} {matched_event.asset.symbol_or_name()}'
            f'{chain_info} via Symbiosis'
        )
        set_bridge_extra_data(
            event=matched_event,
            from_chain=self.node_inquirer.chain_id,
            to_chain=_serialize_chain(dest_chain),
            from_address=matched_event.location_label,
            to_address=None if dest_recipient == ZERO_ADDRESS else dest_recipient,
            transfer_id=transfer_id,
        )
        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_bridge_receive(
            self,
            context: DecoderContext,
            recipient: ChecksumEvmAddress,
            transfer_id: str,
            from_chain: int | None,
            expected_token_addr: ChecksumEvmAddress | None,
            expected_raw_amount: int | None,
            allow_portal_receiver: bool = False,
    ) -> EvmDecodingOutput:
        """Convert the user's incoming receive event into a Symbiosis WITHDRAWAL/BRIDGE event."""
        is_legacy_portal_receiver = allow_portal_receiver and recipient == self.portal
        if is_legacy_portal_receiver:
            def label_matches(label: str | None) -> bool:
                return label is not None and self.base.is_tracked(string_to_evm_address(label))
        elif not self.base.is_tracked(recipient):
            return DEFAULT_EVM_DECODING_OUTPUT
        else:
            def label_matches(label: str | None) -> bool:
                return label == recipient

        matched_event = self._find_bridge_event(
            decoded_events=context.decoded_events,
            is_send=False,
            label_matches=label_matches,
            expected_token_addr=expected_token_addr,
            expected_raw_amount=expected_raw_amount,
        )

        serialized_from_chain = _serialize_chain(from_chain) if from_chain is not None else None
        to_chain_label = self.node_inquirer.chain_id.label()
        if from_chain is not None and (from_label := _chain_label(from_chain)) is not None:
            chain_phrase = f'from {from_label} to {to_chain_label}'
        else:
            chain_phrase = f'to {to_chain_label}'

        if matched_event is not None:
            matched_event.event_type = HistoryEventType.WITHDRAWAL
            matched_event.event_subtype = HistoryEventSubType.BRIDGE
            matched_event.counterparty = CPT_SYMBIOSIS
            matched_event.notes = (
                f'Bridge {matched_event.amount} {matched_event.asset.symbol_or_name()} '
                f'{chain_phrase} via Symbiosis'
            )
            set_bridge_extra_data(
                event=matched_event,
                from_chain=serialized_from_chain,
                to_chain=self.node_inquirer.chain_id,
                to_address=matched_event.location_label,
                transfer_id=transfer_id,
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        if is_legacy_portal_receiver:
            return DEFAULT_EVM_DECODING_OUTPUT

        bridge_extra_data = make_bridge_extra_data(
            from_chain=serialized_from_chain,
            to_chain=self.node_inquirer.chain_id,
            to_address=recipient,
            transfer_id=transfer_id,
        )
        return EvmDecodingOutput(action_items=[ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            location_label=recipient,
            to_event_type=HistoryEventType.WITHDRAWAL,
            to_event_subtype=HistoryEventSubType.BRIDGE,
            to_counterparty=CPT_SYMBIOSIS,
            to_notes=f'Bridge {{amount}} {{symbol}} {chain_phrase} via Symbiosis',
            extra_data=bridge_extra_data,
        )])

    def _decode_request_send(
            self,
            context: DecoderContext,
            resolve_schain: bool,
    ) -> EvmDecodingOutput:
        """Decode Portal SynthesizeRequest or Synthesis BurnRequest outgoing bridge logs."""
        topics = context.tx_log.topics
        data = context.tx_log.data
        if len(topics) < 4 or len(data) < 128:
            log.warning(
                'Malformed Symbiosis %s log in %s tx %s',
                'SynthesizeRequest' if resolve_schain else 'BurnRequest',
                self.node_inquirer.chain_name,
                context.transaction.tx_hash,
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        request_id = data[0:32]
        event_from = bytes_to_address(topics[1])
        dest_chain = int.from_bytes(topics[2])
        dest_recipient: str | None = bytes_to_address(data[32:64])
        raw_amount = int.from_bytes(data[64:96])
        token_addr = bytes_to_address(data[96:128])
        if resolve_schain:
            dest_chain, dest_recipient = self._resolve_final_destination(
                all_logs=context.all_logs,
                request_id=request_id,
                hop_chain_id=dest_chain,
                default_recipient=bytes_to_address(data[32:64]),
            )

        return self._decode_bridge_send(
            context=context,
            event_from=event_from,
            dest_chain=dest_chain,
            dest_recipient=dest_recipient,
            transfer_id=request_id.hex(),
            expected_token_addr=token_addr,
            expected_raw_amount=raw_amount,
        )

    def _decode_refund(self, context: DecoderContext) -> EvmDecodingOutput:
        """Decode RevertSynthesizeCompleted / RevertBurnCompleted as a Symbiosis refund."""
        topics = context.tx_log.topics
        data = context.tx_log.data
        if len(topics) < 3 or len(data) < 96:
            log.warning(
                'Malformed Symbiosis revert refund log in %s tx %s',
                self.node_inquirer.chain_name,
                context.transaction.tx_hash,
            )
            return DEFAULT_EVM_DECODING_OUTPUT

        recipient = bytes_to_address(topics[2])
        raw_amount = int.from_bytes(data[0:32])
        token_addr = bytes_to_address(data[64:96])
        if not self.base.is_tracked(recipient) or token_addr == ZERO_ADDRESS:
            return DEFAULT_EVM_DECODING_OUTPUT

        expected_token, expected_assets = self._resolve_expected_assets(token_addr)
        expected_amount = asset_normalized_value(amount=raw_amount, asset=expected_token)

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == recipient and
                event.counterparty is None and
                event.asset in expected_assets and
                event.amount == expected_amount
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REFUND
                event.counterparty = CPT_SYMBIOSIS
                event.notes = (
                    f'Receive {event.amount} {event.asset.symbol_or_name()} '
                    'as refund from Symbiosis'
                )
                return DEFAULT_EVM_DECODING_OUTPUT

        return EvmDecodingOutput(action_items=[ActionItem(
            action='transform',
            from_event_type=HistoryEventType.RECEIVE,
            from_event_subtype=HistoryEventSubType.NONE,
            asset=expected_asset,
            amount=expected_amount,
            location_label=recipient,
            to_event_type=HistoryEventType.WITHDRAWAL,
            to_event_subtype=HistoryEventSubType.REFUND,
            to_counterparty=CPT_SYMBIOSIS,
            to_notes='Receive {amount} {symbol} as refund from Symbiosis',
        ) for expected_asset in expected_assets])

    def _decode_portal_event(self, context: DecoderContext) -> EvmDecodingOutput:
        if len(topics := context.tx_log.topics) == 0:
            return DEFAULT_EVM_DECODING_OUTPUT

        topic0 = topics[0]
        data = context.tx_log.data

        if topic0 == SYNTHESIZE_REQUEST_TOPIC:
            return self._decode_request_send(context=context, resolve_schain=True)

        if topic0 == BURN_COMPLETED_TOPIC:
            if len(topics) < 4 or len(data) < 96:
                log.warning(
                    'Malformed Symbiosis BurnCompleted log in %s tx %s',
                    self.node_inquirer.chain_name,
                    context.transaction.tx_hash,
                )
                return DEFAULT_EVM_DECODING_OUTPUT
            return self._decode_bridge_receive(
                context=context,
                recipient=bytes_to_address(topics[3]),
                transfer_id=_resolve_transfer_id(cross_chain_id=topics[2], external_id=topics[1]),
                from_chain=None,
                expected_token_addr=bytes_to_address(data[64:96]),
                expected_raw_amount=int.from_bytes(data[0:32]),
                allow_portal_receiver=True,
            )

        if topic0 == REVERT_SYNTHESIZE_COMPLETED_TOPIC:
            return self._decode_refund(context=context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def _decode_synthesis_event(self, context: DecoderContext) -> EvmDecodingOutput:
        if len(topics := context.tx_log.topics) == 0:
            return DEFAULT_EVM_DECODING_OUTPUT

        topic0 = topics[0]
        data = context.tx_log.data

        if topic0 == BURN_REQUEST_TOPIC:
            return self._decode_request_send(context=context, resolve_schain=False)

        if topic0 == BURN_REQUEST_BTC_TOPIC:
            if len(topics) < 3:
                log.warning(
                    'Malformed Symbiosis BurnRequestBTC log in %s tx %s',
                    self.node_inquirer.chain_name,
                    context.transaction.tx_hash,
                )
                return DEFAULT_EVM_DECODING_OUTPUT
            try:
                _, to_bytes, _, _ = decode_abi(
                    types=['uint64', 'bytes', 'uint256', 'uint256'],
                    data=data,
                )
            except DecodingError as e:
                log.warning(
                    'Failed to decode Symbiosis BurnRequestBTC log in %s tx %s: %s',
                    self.node_inquirer.chain_name,
                    context.transaction.tx_hash,
                    e,
                )
                return DEFAULT_EVM_DECODING_OUTPUT
            return self._decode_bridge_send(
                context=context,
                event_from=bytes_to_address(topics[1]),
                dest_chain=SYMBIOSIS_BTC_CHAIN_ID,
                dest_recipient=_decode_btc_recipient(to_bytes),
                transfer_id=None,
                expected_token_addr=None,
                expected_raw_amount=None,
            )

        if topic0 == BURN_REQUEST_TON_TOPIC:
            if len(topics) < 4 or len(data) < 160:
                log.warning(
                    'Malformed Symbiosis BurnRequestTON log in %s tx %s',
                    self.node_inquirer.chain_name,
                    context.transaction.tx_hash,
                )
                return DEFAULT_EVM_DECODING_OUTPUT
            return self._decode_bridge_send(
                context=context,
                event_from=bytes_to_address(topics[1]),
                dest_chain=int.from_bytes(topics[2]),
                dest_recipient=None,
                transfer_id=data[0:32].hex(),
                expected_token_addr=bytes_to_address(data[128:160]),
                expected_raw_amount=int.from_bytes(data[96:128]),
            )

        if topic0 == SYNTHESIZE_COMPLETED_TOPIC:
            if len(topics) < 4:
                log.warning(
                    'Malformed Symbiosis SynthesizeCompleted log in %s tx %s',
                    self.node_inquirer.chain_name,
                    context.transaction.tx_hash,
                )
                return DEFAULT_EVM_DECODING_OUTPUT
            external_id = topics[1]
            is_btc_origin = self._has_synthesis_log(
                all_logs=context.all_logs,
                topic0=BTC_SYNTHESIZE_COMPLETED_TOPIC,
                external_id=external_id,
            )
            return self._decode_bridge_receive(
                context=context,
                recipient=bytes_to_address(topics[2]),
                transfer_id=_resolve_transfer_id(
                    cross_chain_id=topics[3],
                    external_id=external_id,
                ),
                from_chain=SYMBIOSIS_BTC_CHAIN_ID if is_btc_origin else None,
                expected_token_addr=None,
                expected_raw_amount=None,
            )

        if topic0 == BTC_SYNTHESIZE_COMPLETED_TOPIC:
            if len(topics) < 4:
                log.warning(
                    'Malformed Symbiosis BTCSynthesizeCompleted log in %s tx %s',
                    self.node_inquirer.chain_name,
                    context.transaction.tx_hash,
                )
                return DEFAULT_EVM_DECODING_OUTPUT
            external_id = topics[1]
            if self._has_synthesis_log(
                all_logs=context.all_logs,
                topic0=SYNTHESIZE_COMPLETED_TOPIC,
                external_id=external_id,
            ):
                # SynthesizeCompleted is emitted after all MetaRouter/fee transfers finish
                return DEFAULT_EVM_DECODING_OUTPUT
            return self._decode_bridge_receive(
                context=context,
                recipient=bytes_to_address(topics[2]),
                transfer_id=external_id.hex(),
                from_chain=SYMBIOSIS_BTC_CHAIN_ID,
                expected_token_addr=None,
                expected_raw_amount=None,
            )

        if topic0 == REVERT_BURN_COMPLETED_TOPIC:
            return self._decode_refund(context=context)

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        decoders: dict[ChecksumEvmAddress, tuple[Any, ...]] = {}
        if self.portal is not None:
            decoders[self.portal] = (self._decode_portal_event,)
        if self.synthesis is not None:
            decoders[self.synthesis] = (self._decode_synthesis_event,)
        return decoders

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (SYMBIOSIS_CPT_DETAILS,)
