import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.utils import maybe_reshuffle_events
from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.errors.asset import UnknownAsset, WrongAssetType
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int

from .constants import CPT_KYBER

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.evm_event import EvmEvent

KYBER_TRADE_LEGACY = b'\xf7$\xb4\xdff\x17G6\x12\xb5=\x7f\x88\xec\xc6\xea\x980t\xb3\t`\xa0I\xfc\xd0e\x7f\xfe\x80\x80\x83'  # noqa: E501
KYBER_TRADE = b"\xd3\x0c\xa3\x99\xcbCP~\xce\xc6\xa6)\xa3\\\xf4^\xb9\x8c\xdaU\x0c'im\xcb\r\x8cJ8s\xcel"  # noqa: E501
KYBER_LEGACY_CONTRACT = string_to_evm_address('0x9ae49C0d7F8F9EF4B864e004FE86Ac8294E20950')
KYBER_LEGACY_CONTRACT_MIGRATED = string_to_evm_address('0x65bF64Ff5f51272f729BDcD7AcFB00677ced86Cd')  # noqa: E501
KYBER_LEGACY_CONTRACT_UPGRADED = string_to_evm_address('0x9AAb3f75489902f3a48495025729a0AF77d4b11e')  # noqa: E501

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _maybe_update_events_legacy_contrats(
        decoded_events: list['EvmEvent'],
        sender: ChecksumEvmAddress,
        source_asset: CryptoAsset,
        destination_asset: CryptoAsset,
        spent_amount: FVal,
        return_amount: FVal,
        notify_user: Callable[['EvmEvent', str], None],
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
        # it can happen that a spend event get decoded first by an amm decoder. To make sure that
        # the event matches we check both event type and subtype
        if (event.event_type == HistoryEventType.SPEND or event.event_subtype == HistoryEventSubType.SPEND) and event.location_label == sender and event.asset == source_asset and event.balance.amount == spent_amount:  # noqa: E501
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.SPEND
            event.counterparty = CPT_KYBER
            event.notes = f'Swap {event.balance.amount} {crypto_asset.symbol} in kyber'
            out_event = event
        elif (event.event_type == HistoryEventType.RECEIVE or event.event_subtype == HistoryEventSubType.RECEIVE) and event.location_label == sender and event.balance.amount == return_amount and destination_asset == event.asset:  # noqa: E501
            event.event_type = HistoryEventType.TRADE
            event.event_subtype = HistoryEventSubType.RECEIVE
            event.counterparty = CPT_KYBER
            event.notes = f'Receive {event.balance.amount} {crypto_asset.symbol} from kyber swap'
            in_event = event

        maybe_reshuffle_events(ordered_events=[out_event, in_event], events_list=decoded_events)


class KyberDecoder(DecoderInterface):

    def _legacy_contracts_basic_info(self, tx_log: EvmTxReceiptLog) -> tuple[ChecksumEvmAddress, CryptoAsset, CryptoAsset]:  # noqa: E501
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

        source_token = self.base.get_or_create_evm_asset(source_token_address)
        destination_token = self.base.get_or_create_evm_asset(destination_token_address)
        return sender, source_token, destination_token

    def _decode_legacy_trade(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != KYBER_TRADE:
            return DEFAULT_DECODING_OUTPUT

        sender, source_asset, destination_asset = self._legacy_contracts_basic_info(context.tx_log)
        spent_amount_raw = hex_or_bytes_to_int(context.tx_log.data[64:96])
        return_amount_raw = hex_or_bytes_to_int(context.tx_log.data[96:128])
        spent_amount = asset_normalized_value(amount=spent_amount_raw, asset=source_asset)
        return_amount = asset_normalized_value(amount=return_amount_raw, asset=destination_asset)
        _maybe_update_events_legacy_contrats(
            decoded_events=context.decoded_events,
            sender=sender,
            source_asset=source_asset,
            destination_asset=destination_asset,
            spent_amount=spent_amount,
            return_amount=return_amount,
            notify_user=self.notify_user,
        )

        return DEFAULT_DECODING_OUTPUT

    def _decode_legacy_upgraded_trade(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != KYBER_TRADE_LEGACY:
            return DEFAULT_DECODING_OUTPUT

        sender, source_asset, destination_asset = self._legacy_contracts_basic_info(context.tx_log)
        spent_amount_raw = hex_or_bytes_to_int(context.tx_log.data[96:128])
        return_amount_raw = hex_or_bytes_to_int(context.tx_log.data[128:160])
        spent_amount = asset_normalized_value(amount=spent_amount_raw, asset=source_asset)
        return_amount = asset_normalized_value(amount=return_amount_raw, asset=destination_asset)
        _maybe_update_events_legacy_contrats(
            decoded_events=context.decoded_events,
            sender=sender,
            source_asset=source_asset,
            destination_asset=destination_asset,
            spent_amount=spent_amount,
            return_amount=return_amount,
            notify_user=self.notify_user,
        )

        return DEFAULT_DECODING_OUTPUT

    # -- DecoderInterface methods

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            KYBER_LEGACY_CONTRACT: (self._decode_legacy_trade,),
            KYBER_LEGACY_CONTRACT_MIGRATED: (self._decode_legacy_trade,),
            KYBER_LEGACY_CONTRACT_UPGRADED: (self._decode_legacy_upgraded_trade,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(identifier=CPT_KYBER, label='Kyber Legacy', image='kyber.svg'),)  # noqa: E501
