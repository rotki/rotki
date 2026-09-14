import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.across.constants import (
    ACROSS_CPT_DETAILS,
    CPT_ACROSS,
)
from rotkehlchen.chain.evm.decoding.utils import set_bridge_extra_data
from rotkehlchen.chain.solana.decoding.constants import ANCHOR_EVENT_DISCRIMINATOR
from rotkehlchen.chain.solana.decoding.interfaces import SolanaDecoderInterface
from rotkehlchen.chain.solana.decoding.structures import DEFAULT_SOLANA_DECODING_OUTPUT
from rotkehlchen.chain.solana.decoding.utils import get_data_for_discriminator
from rotkehlchen.chain.solana.modules.across.constants import (
    ACROSS_SPOKE_POOL,
    FILLED_RELAY_DISCRIMINATOR,
    FUNDS_DEPOSITED_DISCRIMINATOR,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, SupportedBlockchain
from rotkehlchen.utils.misc import bytes_to_address, bytes_to_solana_address

if TYPE_CHECKING:
    from rotkehlchen.chain.decoding.types import CounterpartyDetails
    from rotkehlchen.chain.solana.decoding.structures import (
        SolanaDecoderContext,
        SolanaDecodingOutput,
    )
    from rotkehlchen.types import SolanaAddress

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _chain_label(chain_id: int) -> str:
    try:
        return ChainID(chain_id).label()
    except ValueError:
        return str(chain_id)


class AcrossDecoder(SolanaDecoderInterface):
    """Decode Across deposits and relay fills on its Solana SpokePool."""

    def _decode_deposit(
            self,
            context: SolanaDecoderContext,
            event_data: bytes,
    ) -> SolanaDecodingOutput:
        depositor = bytes_to_solana_address(event_data[156:188])
        if not self.base.is_tracked(depositor):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        input_token = self.base.get_or_create_solana_token(
            address=bytes_to_solana_address(event_data[:32]),
        )
        input_amount = token_normalized_value(
            token=input_token,
            token_amount=int.from_bytes(event_data[64:72], byteorder='little'),
        )
        destination_chain_id = int.from_bytes(event_data[104:112], byteorder='little')
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == depositor and
                event.asset == input_token and
                event.amount == input_amount and
                event.counterparty is None
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_ACROSS
                event.notes = (
                    f'Bridge {event.amount} {event.asset.symbol_or_name()} from Solana '
                    f'to {_chain_label(destination_chain_id)} via Across'
                )
                set_bridge_extra_data(
                    event=event,
                    from_chain=SupportedBlockchain.SOLANA.serialize(),
                    to_chain=destination_chain_id,
                    from_address=depositor,
                    to_address=bytes_to_address(event_data[188:220]),
                    transfer_id=str(int.from_bytes(event_data[112:144])),
                )
                break
        else:
            log.error(
                'Could not find matching spend event for Solana Across bridge deposit %s',
                context.transaction.signature,
            )

        return DEFAULT_SOLANA_DECODING_OUTPUT

    def _decode_fill(
            self,
            context: SolanaDecoderContext,
            event_data: bytes,
    ) -> SolanaDecodingOutput:
        recipient = bytes_to_solana_address(event_data[320:352])
        if not self.base.is_tracked(recipient):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        output_token = self.base.get_or_create_solana_token(
            address=bytes_to_solana_address(event_data[32:64]),
        )
        output_amount = token_normalized_value(
            token=output_token,
            token_amount=int.from_bytes(event_data[384:392], byteorder='little'),
        )
        origin_chain_id = int.from_bytes(event_data[112:120], byteorder='little')
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == recipient and
                event.asset == output_token and
                event.amount == output_amount and
                event.counterparty is None
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_ACROSS
                event.notes = (
                    f'Bridge {event.amount} {event.asset.symbol_or_name()} '
                    f'from {_chain_label(origin_chain_id)} to Solana via Across'
                )
                set_bridge_extra_data(
                    event=event,
                    from_chain=origin_chain_id,
                    to_chain=SupportedBlockchain.SOLANA.serialize(),
                    from_address=bytes_to_address(event_data[224:256]),
                    to_address=recipient,
                    transfer_id=str(int.from_bytes(event_data[120:152])),
                )
                break
        else:
            log.error(
                'Could not find matching receive event for Solana Across bridge fill %s',
                context.transaction.signature,
            )

        return DEFAULT_SOLANA_DECODING_OUTPUT

    def decode_bridge(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        if (event_data := get_data_for_discriminator(
            data=context.instruction.data,
            discriminator=ANCHOR_EVENT_DISCRIMINATOR,
        )) is None:
            return DEFAULT_SOLANA_DECODING_OUTPUT

        if (fill_data := get_data_for_discriminator(
            data=event_data,
            discriminator=FILLED_RELAY_DISCRIMINATOR,
        )) is not None:
            return self._decode_fill(context=context, event_data=fill_data)
        if (deposit_data := get_data_for_discriminator(
            data=event_data,
            discriminator=FUNDS_DEPOSITED_DISCRIMINATOR,
        )) is not None:
            return self._decode_deposit(context=context, event_data=deposit_data)
        return DEFAULT_SOLANA_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[SolanaAddress, tuple[Any, ...]]:
        return {ACROSS_SPOKE_POOL: (self.decode_bridge,)}

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (ACROSS_CPT_DETAILS,)
