from typing import TYPE_CHECKING, Any

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.solana.decoding.interfaces import SolanaDecoderInterface
from rotkehlchen.chain.solana.decoding.structures import DEFAULT_SOLANA_DECODING_OUTPUT
from rotkehlchen.chain.solana.modules.jito.constants import CPT_JITO, JITO_TIP_PAYMENT_ACCOUNTS
from rotkehlchen.constants.assets import A_SOL
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.types import SolanaAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.decoding.structures import (
        SolanaDecodingOutput,
        SolanaEventDecoderContext,
    )


class JitoDecoder(SolanaDecoderInterface):

    def decode_jito_tip(self, context: 'SolanaEventDecoderContext') -> 'SolanaDecodingOutput':
        """Decode Jito tip events.
        https://jito-foundation.gitbook.io/mev/mev-payment-and-distribution/tip-payment-program
        """
        if context.event.event_type != HistoryEventType.SPEND or context.event.asset != A_SOL:
            return DEFAULT_SOLANA_DECODING_OUTPUT

        context.event.event_subtype = HistoryEventSubType.FEE
        context.event.counterparty = CPT_JITO
        context.event.notes = f'Spend {context.event.amount} SOL as Jito tip'
        return DEFAULT_SOLANA_DECODING_OUTPUT

    def transfer_addresses_to_decoders(self) -> dict[SolanaAddress, tuple[Any, ...]]:
        return dict.fromkeys(JITO_TIP_PAYMENT_ACCOUNTS, (self.decode_jito_tip,))

    @staticmethod
    def counterparties() -> tuple['CounterpartyDetails', ...]:
        return (CounterpartyDetails(
            identifier=CPT_JITO,
            label='Jito',
            image='jito_light.png',
            darkmode_image='jito_dark.png',
        ),)
