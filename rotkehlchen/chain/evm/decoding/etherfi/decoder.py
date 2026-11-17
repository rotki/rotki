from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import asset_normalized_value
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import DEFAULT_EVM_DECODING_OUTPUT
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.utils.misc import bytes_to_address

from .constants import (
    CASHBACK,
    CPT_ETHERFI,
    ETHERFI_CASH_EVENT_EMITTER,
    ETHERFI_COUNTERPARTY_DETAILS,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.evm.decoding.structures import DecoderContext, EvmDecodingOutput
    from rotkehlchen.types import ChecksumEvmAddress


class EtherfiCashCommonDecoder(EvmDecoderInterface):

    def _decode_cash_events(self, context: DecoderContext) -> EvmDecodingOutput:
        if (
            context.tx_log.topics[0] != CASHBACK or
            int.from_bytes(context.tx_log.topics[3]) == 0 or  # not paid out yet
            not self.base.is_tracked(recipient := bytes_to_address(context.tx_log.topics[2]))
        ):
            return DEFAULT_EVM_DECODING_OUTPUT

        token = self.base.get_or_create_evm_token(address=bytes_to_address(context.tx_log.data[32:64]))  # noqa: E501
        amount = asset_normalized_value(amount=int.from_bytes(context.tx_log.data[64:96]), asset=token)  # noqa: E501
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == recipient and
                event.asset == token and
                event.amount == amount
            ):
                event.event_subtype = HistoryEventSubType.CASHBACK
                event.counterparty = CPT_ETHERFI
                event.notes = f'Receive cashback of {amount} {token.symbol} from ether.fi card'
                break

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return {ETHERFI_CASH_EVENT_EMITTER: (self._decode_cash_events,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (ETHERFI_COUNTERPARTY_DETAILS,)
