import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.assets.utils import token_normalized_value
from rotkehlchen.chain.evm.decoding.cctp.constants import (
    CCTP_CPT_DETAILS,
    CCTP_DOMAIN_MAPPING,
    CPT_CCTP,
)
from rotkehlchen.chain.evm.decoding.utils import set_bridge_extra_data
from rotkehlchen.chain.solana.decoding.interfaces import SolanaDecoderInterface
from rotkehlchen.chain.solana.decoding.structures import DEFAULT_SOLANA_DECODING_OUTPUT
from rotkehlchen.chain.solana.modules.cctp.constants import (
    CCTP_MESSAGE_TRANSMITTER_V2,
    CCTP_TOKEN_MESSENGER_V2,
    DEPOSIT_FOR_BURN_DISCRIMINATOR,
    RECEIVE_MESSAGE_DISCRIMINATOR,
)
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SupportedBlockchain
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


class CctpDecoder(SolanaDecoderInterface):
    """Decode Circle CCTP V2 USDC transfers originating from or arriving on Solana."""

    def decode_deposit(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        instruction = context.instruction
        if (
            len(instruction.data) < 96 or
            instruction.data[:8] != DEPOSIT_FOR_BURN_DISCRIMINATOR or
            len(instruction.accounts) < 11 or
            not self.base.is_tracked(depositor := instruction.accounts[0])
        ):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        amount = int.from_bytes(instruction.data[8:16], byteorder='little')
        destination_domain = int.from_bytes(instruction.data[16:20], byteorder='little')
        if (destination_chain := CCTP_DOMAIN_MAPPING.get(destination_domain)) is None:
            log.error(
                'Could not find destination domain %s for Solana CCTP bridge %s',
                destination_domain,
                context.transaction.signature,
            )
            return DEFAULT_SOLANA_DECODING_OUTPUT

        mint_recipient = bytes_to_address(instruction.data[20:52])
        token = self.base.get_or_create_solana_token(address=instruction.accounts[10])
        normalized_amount = token_normalized_value(token=token, token_amount=amount)
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.SPEND and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == depositor and
                event.asset == token and
                event.amount == normalized_amount
            ):
                event.event_type = HistoryEventType.DEPOSIT
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_CCTP
                event.notes = (
                    f'Bridge {event.amount} {event.asset.symbol_or_name()} from Solana '
                    f'to {destination_chain.label()} via CCTP'
                )
                set_bridge_extra_data(
                    event=event,
                    from_chain=SupportedBlockchain.SOLANA.serialize(),
                    to_chain=destination_chain,
                    from_address=depositor,
                    to_address=mint_recipient,
                )
                break
        else:
            log.error(
                'Could not find matching burn event for Solana CCTP bridge %s',
                context.transaction.signature,
            )

        return DEFAULT_SOLANA_DECODING_OUTPUT

    def decode_receive(self, context: SolanaDecoderContext) -> SolanaDecodingOutput:
        instruction_data = context.instruction.data
        if (
            len(instruction_data) < 12 or
            instruction_data[:8] != RECEIVE_MESSAGE_DISCRIMINATOR
        ):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        message_length = int.from_bytes(instruction_data[8:12], byteorder='little')
        message = instruction_data[12:12 + message_length]
        if len(message) < 344:
            log.error(
                'Encountered malformed CCTP V2 receive message in Solana transaction %s',
                context.transaction.signature,
            )
            return DEFAULT_SOLANA_DECODING_OUTPUT

        source_domain = int.from_bytes(message[4:8])
        if (source_chain := CCTP_DOMAIN_MAPPING.get(source_domain)) is None:
            log.error(
                'Could not find source domain %s for Solana CCTP bridge %s',
                source_domain,
                context.transaction.signature,
            )
            return DEFAULT_SOLANA_DECODING_OUTPUT

        message_body = message[148:]
        recipient_token_account = bytes_to_solana_address(message_body[36:68])
        if (recipient_data := context.ata_data.get(recipient_token_account)) is None:
            log.error(
                'Could not find recipient token account %s for Solana CCTP bridge %s',
                recipient_token_account,
                context.transaction.signature,
            )
            return DEFAULT_SOLANA_DECODING_OUTPUT

        recipient, mint = recipient_data
        if not self.base.is_tracked(recipient):
            return DEFAULT_SOLANA_DECODING_OUTPUT

        token = self.base.get_or_create_solana_token(address=mint)
        raw_amount = int.from_bytes(message_body[68:100])
        fee = int.from_bytes(message_body[164:196])
        amount = token_normalized_value(token=token, token_amount=raw_amount - fee)
        for event in context.decoded_events:
            if (
                event.event_type == HistoryEventType.RECEIVE and
                event.event_subtype == HistoryEventSubType.NONE and
                event.location_label == recipient and
                event.asset == token and
                event.amount == amount
            ):
                event.event_type = HistoryEventType.WITHDRAWAL
                event.event_subtype = HistoryEventSubType.BRIDGE
                event.counterparty = CPT_CCTP
                event.notes = (
                    f'Bridge {event.amount} {event.asset.symbol_or_name()} '
                    f'from {source_chain.label()} to Solana via CCTP'
                )
                set_bridge_extra_data(
                    event=event,
                    from_chain=source_chain,
                    to_chain=SupportedBlockchain.SOLANA.serialize(),
                    from_address=bytes_to_address(message_body[100:132]),
                    to_address=recipient_token_account,
                    transfer_id=f'0x{message[12:44].hex()}',
                )
                break
        else:
            log.error(
                'Could not find matching receive event for Solana CCTP bridge %s',
                context.transaction.signature,
            )

        return DEFAULT_SOLANA_DECODING_OUTPUT

    def addresses_to_decoders(self) -> dict[SolanaAddress, tuple[Any, ...]]:
        return {
            CCTP_TOKEN_MESSENGER_V2: (self.decode_deposit,),
            CCTP_MESSAGE_TRANSMITTER_V2: (self.decode_receive,),
        }

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CCTP_CPT_DETAILS,)
