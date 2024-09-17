from typing import Any

from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.gnosis.modules.gnosis_pay.constants import (
    CPT_GNOSIS_PAY,
    GNOSIS_PAY_CASHBACK_ADDRESS,
    GNOSIS_PAY_CPT_DETAILS,
    GNOSIS_PAY_SPENDER_ADDRESS,
    SPEND,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import hex_or_bytes_to_address, hex_or_bytes_to_int


class GnosisPayDecoder(DecoderInterface):

    def decode_cashback_events(self, context: DecoderContext) -> DecodingOutput:
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset.identifier == 'eip155:100/erc20:0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb'  # noqa: E501
            ):
                event.counterparty = CPT_GNOSIS_PAY
                event.event_subtype = HistoryEventSubType.CASHBACK
                event.notes = f'Receive cashback of {event.balance.amount} GNO from Gnosis Pay'

        return DEFAULT_DECODING_OUTPUT

    def decode_spend(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != SPEND:
            return DEFAULT_DECODING_OUTPUT

        token = self.base.get_or_create_evm_token(
            address=hex_or_bytes_to_address(context.tx_log.data[0:32]),
        )
        # Account is the roles module, which is the 2nd module in the array
        # when doing getModulesPaginated("0x0000000000000000000000000000000000000001")
        # with pageSize 100
        # hex_or_bytes_to_address(context.tx_log.data[32:64])  # noqa: ERA001
        # should we use it?
        raw_amount = hex_or_bytes_to_int(context.tx_log.data[96:128])
        amount = token_normalized_value(raw_amount, token)

        for event in context.decoded_events:
            if (
                    event.event_type == HistoryEventType.SPEND and
                    event.event_subtype == HistoryEventSubType.NONE and
                    event.asset == token and
                    event.balance.amount == amount
            ):
                event.counterparty = CPT_GNOSIS_PAY
                event.event_subtype = HistoryEventSubType.PAYMENT
                event.notes = f'Spend {event.balance.amount} {token.symbol} via Gnosis Pay'

        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {
            GNOSIS_PAY_CASHBACK_ADDRESS: (self.decode_cashback_events,),
            GNOSIS_PAY_SPENDER_ADDRESS: (self.decode_spend,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (GNOSIS_PAY_CPT_DETAILS,)
