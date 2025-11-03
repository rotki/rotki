from dataclasses import dataclass
from typing import Final

from rotkehlchen.chain.decoding.structures import CommonDecodingOutput
from rotkehlchen.chain.solana.types import SolanaInstruction, SolanaTransaction
from rotkehlchen.history.events.structures.solana_event import SolanaEvent


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class SolanaDecoderContext:
    """Arguments context for decoding rules"""
    instruction: SolanaInstruction
    transaction: SolanaTransaction
    decoded_events: list[SolanaEvent]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class SolanaEventDecoderContext:
    """Arguments context for decoding rules"""
    event: SolanaEvent
    transaction: SolanaTransaction
    decoded_events: list[SolanaEvent]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class SolanaDecodingOutput(CommonDecodingOutput[SolanaEvent]):
    ...


DEFAULT_SOLANA_DECODING_OUTPUT: Final = SolanaDecodingOutput()
