from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry

T_Event = TypeVar('T_Event', bound='HistoryBaseEntry')


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class CommonDecodingOutput(Generic[T_Event]):
    """Output of decoding functions

    - events can be returned if the decoding method has generated new events and they need to be
    added to the list of other decoded events.
    - refresh_balances may be set to True if the user's on-chain balances in some protocols has
    changed (for example if the user has deposited / withdrawn funds from a curve gauge).
    - reload_decoders can be None in which case nothing happens. Or a set of decoders names
    for which to reload data. The decoder's name is the class name without the Decoder suffix.
    For example Eigenlayer for EigenlayerDecoder
    """
    events: list[T_Event] | None = None
    refresh_balances: bool = False
    reload_decoders: set[str] | None = None
