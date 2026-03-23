from typing import Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.interfaces import EvmDecoderInterface
from rotkehlchen.chain.evm.decoding.structures import (
    DEFAULT_EVM_DECODING_OUTPUT,
    DecoderContext,
    EvmDecodingOutput,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import bytes_to_address

from .constants import ERC4337_ENTRYPOINTS, USER_OPERATION_EVENT


class Erc4337Decoder(EvmDecoderInterface):
    def _decode_entrypoint_event(self, context: DecoderContext) -> EvmDecodingOutput:
        if context.tx_log.topics[0] != USER_OPERATION_EVENT or len(context.tx_log.topics) < 3:
            return DEFAULT_EVM_DECODING_OUTPUT

        if (entrypoint := context.tx_log.address) not in ERC4337_ENTRYPOINTS:
            return DEFAULT_EVM_DECODING_OUTPUT

        if not self.base.is_tracked(user_address := bytes_to_address(context.tx_log.topics[2])):
            return DEFAULT_EVM_DECODING_OUTPUT

        native_token = self.node_inquirer.native_token
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.asset == native_token and
                event.location_label == user_address and
                event.address == entrypoint
            ):
                event.event_subtype = HistoryEventSubType.FEE
                event.notes = f'Spend {event.amount} {native_token.symbol} as ERC-4337 fee via {entrypoint}'  # noqa: E501
                return DEFAULT_EVM_DECODING_OUTPUT

        return DEFAULT_EVM_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[ChecksumEvmAddress, tuple[Any, ...]]:
        return dict.fromkeys(ERC4337_ENTRYPOINTS, (self._decode_entrypoint_event,))

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return ()
