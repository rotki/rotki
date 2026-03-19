from dataclasses import dataclass
from typing import Final

from rotkehlchen.chain.decoding.structures import CommonDecodingOutput
from rotkehlchen.chain.starknet.types import StarknetTransaction
from rotkehlchen.history.events.structures.starknet_event import StarknetEvent


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class StarknetDecoderContext:
    """Arguments context for decoding rules"""
    transaction: StarknetTransaction
    decoded_events: list[StarknetEvent]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class StarknetEventDecoderContext:
    """Arguments context for enricher rules"""
    event: StarknetEvent
    transaction: StarknetTransaction
    decoded_events: list[StarknetEvent]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class StarknetDecodingOutput(CommonDecodingOutput[StarknetEvent]):
    ...


DEFAULT_STARKNET_DECODING_OUTPUT: Final = StarknetDecodingOutput()
