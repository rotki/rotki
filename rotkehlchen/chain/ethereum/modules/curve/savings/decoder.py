from typing import Any, Final

from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS, ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE, CURVE_COUNTERPARTY_DETAILS
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress

from .constants import SCRV_TOKEN_ADDRESS

DEPOSIT_TOPIC: Final = b'\xdc\xbc\x1c\x05$\x0f1\xff:\xd0g\xef\x1e\xe3\\\xe4\x99wbu.:\tR\x84uED\xf4\xc7\t\xd7'  # noqa: E501
REDEEM_TOPIC: Final = b'\xfb\xdey} \x1ch\x1b\x91\x05e)\x11\x9e\x0b\x02@|{\xb9jJ,u\xc0\x1f\xc9fr2\xc8\xdb'  # noqa: E501


class CurvesavingsDecoder(DecoderInterface):

    def _decode_deposit_or_withdrawal(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] not in (DEPOSIT_TOPIC, REDEEM_TOPIC):
            return DEFAULT_DECODING_OUTPUT

        assets_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[:32]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        shares_amount = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=DEFAULT_TOKEN_DECIMALS,
        )
        for event in context.decoded_events:
            if (
                    event.amount == assets_amount and
                    event.address == SCRV_TOKEN_ADDRESS and
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE
            ):
                event.counterparty = CPT_CURVE
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                event.notes = f'Deposit {event.amount} {event.asset.resolve_to_asset_with_symbol().symbol} in Curve Savings'  # noqa: E501

            elif (
                    event.amount == shares_amount and
                    event.address == ZERO_ADDRESS and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE
            ):
                event.counterparty = CPT_CURVE
                event.event_type = HistoryEventType.RECEIVE
                event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                event.notes = f'Receive {shares_amount} {event.asset.resolve_to_asset_with_symbol().symbol} from depositing into Curve Savings'  # noqa: E501

            elif (
                    event.amount == shares_amount and
                    event.address == ZERO_ADDRESS and
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE
            ):
                event.counterparty = CPT_CURVE
                event.event_type = HistoryEventType.SPEND
                event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                event.notes = f'Return {shares_amount} {event.asset.resolve_to_asset_with_symbol().symbol} into Curve Savings'  # noqa: E501

            elif (
                    event.amount == assets_amount and
                    event.address == SCRV_TOKEN_ADDRESS and
                    event.event_type == HistoryEventType.RECEIVE and
                    event.event_subtype == HistoryEventSubType.NONE
            ):
                event.counterparty = CPT_CURVE
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                event.notes = f'Remove {assets_amount} {event.asset.resolve_to_asset_with_symbol().symbol} from Curve Savings'  # noqa: E501

        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {SCRV_TOKEN_ADDRESS: (self._decode_deposit_or_withdrawal,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CURVE_COUNTERPARTY_DETAILS,)
