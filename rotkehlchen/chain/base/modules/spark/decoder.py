from typing import TYPE_CHECKING, Any, Final

from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.decoding.interfaces import DecoderInterface
from rotkehlchen.chain.evm.decoding.spark.constants import CPT_SPARK, SPARK_COUNTERPARTY_DETAILS
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_DECODING_OUTPUT,
    DecoderContext,
    DecodingOutput,
)
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails

SWAP_EXACT_IN_4BYTE: Final = b'\x1a\x01\x9e7'
SWAP_TOPIC: Final = b'\xdb\xa4>\xe9\x91l\xb1V\xcc2\xa5\xd3@n\x874\x1eV\x81&\xa4h\x15)@s\xba%\xc9@\x02F'  # noqa: E501

SPARK_PSM_ADDRESS: Final = string_to_evm_address('0x1601843c5E9bC251A3272907010AFa41Fa18347E')


class SparkDecoder(DecoderInterface):

    def _decode_deposit_withdrawal(self, context: DecoderContext) -> DecodingOutput:
        if context.tx_log.topics[0] != SWAP_TOPIC:
            return DEFAULT_DECODING_OUTPUT

        if not self.base.is_tracked(receiver := bytes_to_address(context.tx_log.topics[3])):
            return DEFAULT_DECODING_OUTPUT

        asset_in = self.base.get_or_create_evm_token(bytes_to_address(context.tx_log.topics[1]))
        asset_out = self.base.get_or_create_evm_token(bytes_to_address(context.tx_log.topics[2]))
        amount_in = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[32:64]),
            token_decimals=asset_in.decimals,
        )
        amount_out = token_normalized_value_decimals(
            token_amount=int.from_bytes(context.tx_log.data[64:96]),
            token_decimals=asset_out.decimals,
        )
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == amount_in and
                event.location_label == receiver and
                event.asset == asset_in
            ):
                event.counterparty = CPT_SPARK
                if context.transaction.input_data[:4] == SWAP_EXACT_IN_4BYTE:
                    event.event_type = HistoryEventType.DEPOSIT
                    event.event_subtype = HistoryEventSubType.DEPOSIT_FOR_WRAPPED
                    event.notes = f'Deposit {amount_in} {asset_in.symbol} in Spark Savings'
                else:  # swap exact out
                    event.event_subtype = HistoryEventSubType.RETURN_WRAPPED
                    event.notes = f'Return {amount_in} {asset_in.symbol} into Spark Savings'

            elif (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.amount == amount_out and
                event.location_label == receiver and
                event.asset == asset_out
            ):
                event.counterparty = CPT_SPARK
                if context.transaction.input_data[:4] == SWAP_EXACT_IN_4BYTE:
                    event.event_type = HistoryEventType.RECEIVE
                    event.event_subtype = HistoryEventSubType.RECEIVE_WRAPPED
                    event.notes = f'Receive {amount_out} {asset_out.symbol} from depositing into Spark Savings'  # noqa: E501
                else:  # swap exact out
                    event.event_type = HistoryEventType.WITHDRAWAL
                    event.event_subtype = HistoryEventSubType.REDEEM_WRAPPED
                    event.notes = f'Remove {amount_out} {asset_out.symbol} from Spark Savings'

        return DEFAULT_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {SPARK_PSM_ADDRESS: (self._decode_deposit_withdrawal,)}

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (SPARK_COUNTERPARTY_DETAILS,)
