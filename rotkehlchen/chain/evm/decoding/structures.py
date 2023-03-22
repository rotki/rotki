from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Literal, NamedTuple, Optional

if TYPE_CHECKING:
    from rotkehlchen.accounting.structures.evm_event import EvmEvent
    from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
    from rotkehlchen.assets.asset import Asset, EvmToken
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.fval import FVal
    from rotkehlchen.types import EvmTransaction


class ActionItem(NamedTuple):
    """Action items to propagate to other decoders during decoding"""
    action: Literal['transform', 'skip', 'skip & keep']
    sequence_index: int
    from_event_type: 'HistoryEventType'
    from_event_subtype: 'HistoryEventSubType'
    asset: 'Asset'
    amount: 'FVal'
    to_event_type: Optional['HistoryEventType'] = None
    to_event_subtype: Optional['HistoryEventSubType'] = None
    to_notes: Optional[str] = None
    to_counterparty: Optional[str] = None
    extra_data: Optional[dict] = None
    # Optional event data that pairs it with the event of the action item
    # Contains a tuple with the paired event and whether it's an out event (True) or in event
    paired_event_data: Optional[tuple['EvmEvent', bool]] = None


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class BasicContext:
    """Common elements between different contexts in the decoding logic"""
    tx_log: 'EvmTxReceiptLog'
    transaction: 'EvmTransaction'
    action_items: list[ActionItem]
    all_logs: list['EvmTxReceiptLog']


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DecoderContext(BasicContext):
    """Context given to decoding rules"""
    decoded_events: list['EvmEvent']


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class EnricherContext(BasicContext):
    """Context for enrichment rules"""
    token: 'EvmToken'
    event: 'EvmEvent'


class DecodingOutput(NamedTuple):
    """
    Output of decoding functions
    Counterparty is set to the counterparty that modified the transaction
    """
    event: Optional['EvmEvent'] = None
    action_items: list[ActionItem] = []
    counterparty: Optional[str] = None


class TransferEnrichmentOutput(NamedTuple):
    """
    Return structure for the enrichment functions.
    Counterparty is set to the counterparty that modified the transaction
    """
    counterparty: Optional[str] = None


DEFAULT_DECODING_OUTPUT: Final = DecodingOutput()
DEFAULT_ENRICHMENT_OUTPUT: Final = TransferEnrichmentOutput()
