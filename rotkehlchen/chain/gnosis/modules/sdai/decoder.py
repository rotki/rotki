from typing import Any

from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.constants import (
    CPT_SDAI,
    SDAI_CPT_DETAILS,
    SDAI_DEPOSIT,
    SDAI_REDEEM,
)
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.gnosis.modules.sdai.constants import GNOSIS_SDAI_ADDRESS
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress

from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS  # all tokens in this decoder use default(18)  # noqa: E501 # isort: skip


class SdaiDecoder(DecoderInterface):

    def _decode_sdai_deposit_events(self, context: DecoderContext) -> DecodingOutput:
        amount_raw = int.from_bytes(context.tx_log.data[:32])
        amount = token_normalized_value_decimals(amount_raw, DEFAULT_TOKEN_DECIMALS)
        shares_raw = int.from_bytes(context.tx_log.data[32:64])
        shares = token_normalized_value_decimals(shares_raw, DEFAULT_TOKEN_DECIMALS)

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == amount
            ):
                asset = event.asset.resolve_to_crypto_asset()
                event.counterparty = CPT_SDAI
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.notes = f'Deposit {event.amount} {asset.symbol} into the Savings xDAI contract'  # noqa: E501
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == shares
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.notes = f'Withdraw {event.amount} sDAI from the Savings xDAI contract'
                event.counterparty = CPT_SDAI

        return DEFAULT_DECODING_OUTPUT

    def _decode_sdai_redeem_events(self, context: DecoderContext) -> DecodingOutput:
        amount_raw = int.from_bytes(context.tx_log.data[:32])
        amount = token_normalized_value_decimals(amount_raw, DEFAULT_TOKEN_DECIMALS)
        shares_raw = int.from_bytes(context.tx_log.data[32:64])
        shares = token_normalized_value_decimals(shares_raw, DEFAULT_TOKEN_DECIMALS)

        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == shares
            ):
                event.event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                event.event_type = HistoryEventType.DEPOSIT
                event.notes = f'Return {event.amount} sDAI to the Savings xDAI contract'
                event.counterparty = CPT_SDAI
            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == amount
            ):
                asset = event.asset.resolve_to_crypto_asset()
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REMOVE_ASSET
                event.notes = f'Withdraw {event.amount} {asset.symbol} from the Savings xDAI contract'  # noqa: E501
                event.counterparty = CPT_SDAI

        return DEFAULT_DECODING_OUTPUT

    def decode_sdai_events(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] == SDAI_DEPOSIT:
            return self._decode_sdai_deposit_events(context)
        if context.tx_log.topics[0] == SDAI_REDEEM:
            return self._decode_sdai_redeem_events(context)

        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {GNOSIS_SDAI_ADDRESS: (self.decode_sdai_events,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (SDAI_CPT_DETAILS,)
