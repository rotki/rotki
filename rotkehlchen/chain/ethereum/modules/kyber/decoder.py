import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Tuple

from rotkehlchen.accounting.structures.base import HistoryBaseEntry
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.chain.ethereum.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.ethereum.decoding.structures import ActionItem
from rotkehlchen.chain.ethereum.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.ethereum.structures import EthereumTxReceiptLog
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.chain.ethereum.utils import asset_normalized_value, ethaddress_to_asset
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, EvmTransaction
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CPT_KYBER

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.ethereum.manager import EthereumManager

KYBER_TRADE_LEGACY = b'\xf7$\xb4\xdff\x17G6\x12\xb5=\x7f\x88\xec\xc6\xea\x980t\xb3\t`\xa0I\xfc\xd0e\x7f\xfe\x80\x80\x83'  # noqa: E501
KYBER_LEGACY_CONTRACT = string_to_evm_address('0x9ae49C0d7F8F9EF4B864e004FE86Ac8294E20950')
KYBER_LEGACY_CONTRACT_MIGRATED = string_to_evm_address('0x65bF64Ff5f51272f729BDcD7AcFB00677ced86Cd')  # noqa: E501
KYBER_LEGACY_CONTRACT_UPGRADED = string_to_evm_address('0x9AAb3f75489902f3a48495025729a0AF77d4b11e')  # noqa: E501

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _legacy_contracts_basic_info(tx_log: EthereumTxReceiptLog) -> Tuple[ChecksumEvmAddress, Optional[CryptoAsset], Optional[CryptoAsset]]:  # noqa: E501
    """
    Returns:
    - address of the sender
    - source token (can be none)
    - destination token (can be none)
    May raise:
    - DeserializationError when using hex_or_bytes_to_address
    """
    sender = hex_or_bytes_to_address(tx_log.topics[1])
    source_token_address = hex_or_bytes_to_address(tx_log.data[:32])
    destination_token_address = hex_or_bytes_to_address(tx_log.data[32:64])

    source_token = ethaddress_to_asset(source_token_address)
    destination_token = ethaddress_to_asset(destination_token_address)
    return sender, source_token, destination_token


def _maybe_update_events_legacy_contrats(
    decoded_events: List[HistoryBaseEntry],
    sender: ChecksumEvmAddress,
    source_asset: CryptoAsset,
    destination_asset: CryptoAsset,
    spent_amount: FVal,
    return_amount: FVal,
    notify_user: Callable[[HistoryBaseEntry, str], None],
) -> None:
    """
    Use the information from a trade transaction to modify the HistoryEvents from receive/send to
    trade if the conditions are correct.
    """
    in_event = out_event = None
    for event in decoded_events:
        try:
            crypto_asset = event.asset.resolve_to_crypto_asset()
        except (UnknownAsset, WrongAssetType):
            notify_user(event, CPT_KYBER)
            continue
        if event.event_type == HistoryEventType.SPEND and event.location_label == sender and event.asset == source_asset and event.balance.amount == spent_amount:  # noqa: E501
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.SPEND
            event.counterparty = CPT_KYBER
            event.notes = f'Swap {event.balance.amount} {crypto_asset.symbol} in kyber'
            out_event = event
        elif event.event_type == HistoryEventType.RECEIVE and event.location_label == sender and event.balance.amount == return_amount and destination_asset == event.asset:  # noqa: E501
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.RECEIVE
            event.counterparty = CPT_KYBER
            event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} from kyber swap'  # noqa: E501
            in_event = event

        maybe_reshuffle_events(out_event=out_event, in_event=in_event)


class KyberDecoder(DecoderInterface):
    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            ethereum_manager=ethereum_manager,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
        )

    def _decode_legacy_trade(  # pylint: disable=no-self-use
        self,
        tx_log: EthereumTxReceiptLog,
        transaction: EvmTransaction,  # pylint: disable=unused-argument
        decoded_events: List[HistoryBaseEntry],
        all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
        action_items: Optional[List[ActionItem]],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], List[ActionItem]]:
        if tx_log.topics[0] == KYBER_TRADE_LEGACY:
            return None, []

        sender, source_asset, destination_asset = _legacy_contracts_basic_info(tx_log)
        if source_asset is None or destination_asset is None:
            return None, []

        spent_amount_raw = hex_or_bytes_to_int(tx_log.data[64:96])
        return_amount_raw = hex_or_bytes_to_int(tx_log.data[96:128])
        spent_amount = asset_normalized_value(amount=spent_amount_raw, asset=source_asset)
        return_amount = asset_normalized_value(amount=return_amount_raw, asset=destination_asset)
        _maybe_update_events_legacy_contrats(
            decoded_events=decoded_events,
            sender=sender,
            source_asset=source_asset,
            destination_asset=destination_asset,
            spent_amount=spent_amount,
            return_amount=return_amount,
            notify_user=self.notify_user,
        )

        return None, []

    def _decode_legacy_upgraded_trade(  # pylint: disable=no-self-use
        self,
        tx_log: EthereumTxReceiptLog,
        transaction: EvmTransaction,  # pylint: disable=unused-argument
        decoded_events: List[HistoryBaseEntry],
        all_logs: List[EthereumTxReceiptLog],  # pylint: disable=unused-argument
        action_items: Optional[List[ActionItem]],  # pylint: disable=unused-argument
    ) -> Tuple[Optional[HistoryBaseEntry], List[ActionItem]]:
        if tx_log.topics[0] != KYBER_TRADE_LEGACY:
            return None, []

        sender, source_asset, destination_asset = _legacy_contracts_basic_info(tx_log)
        if source_asset is None or destination_asset is None:
            return None, []

        spent_amount_raw = hex_or_bytes_to_int(tx_log.data[96:128])
        return_amount_raw = hex_or_bytes_to_int(tx_log.data[128:160])
        spent_amount = asset_normalized_value(amount=spent_amount_raw, asset=source_asset)
        return_amount = asset_normalized_value(amount=return_amount_raw, asset=destination_asset)
        _maybe_update_events_legacy_contrats(
            decoded_events=decoded_events,
            sender=sender,
            source_asset=source_asset,
            destination_asset=destination_asset,
            spent_amount=spent_amount,
            return_amount=return_amount,
            notify_user=self.notify_user,
        )

        return None, []

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> Dict[ChecksumEvmAddress, Tuple[Any, ...]]:
        return {
            KYBER_LEGACY_CONTRACT: (self._decode_legacy_trade,),
            KYBER_LEGACY_CONTRACT_MIGRATED: (self._decode_legacy_trade,),
            KYBER_LEGACY_CONTRACT_UPGRADED: (self._decode_legacy_upgraded_trade,),
        }

    def counterparties(self) -> List[str]:
        return [CPT_KYBER]
