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
class DecoderBasicContext:
    """Common elements between different contexts in the decoding logic"""
    tx_log: 'EvmTxReceiptLog'
    transaction: 'EvmTransaction'
    action_items: list[ActionItem]
    all_logs: list['EvmTxReceiptLog']


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DecoderContext(DecoderBasicContext):
    """Arguments context for decoding rules"""
    decoded_events: list['EvmEvent']


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class EnricherContext(DecoderBasicContext):
    """Arguments context for enrichment rules"""
    token: 'EvmToken'
    event: 'EvmEvent'


class DecodingOutput(NamedTuple):
    """
    Output of decoding functions

    - event can be returned if the decodeing method has generated a new event and it needs to be
    added to the list of other decoded events.
    - action_items is a list of actions to be performed later automatically or to be passed
    in further decoding methods.
    - matched_counterparty is optionally set if needed for decoder rules that matched
    and is used in post-decoding rules like in the case of balancer
    - refresh_balances may be set to True if the user's on-chain balances in some protocols has
    changed (for example if the user has deposited / withdrawn funds from a curve gauge).
    """
    event: Optional['EvmEvent'] = None
    action_items: list[ActionItem] = []
    matched_counterparty: Optional[str] = None
    refresh_balances: bool = False


class TransferEnrichmentOutput(NamedTuple):
    """
    Return structure for the enrichment functions.

    - matched_counterparty is optionally set if needed for enrichment rules
    and is used in post-decoding rules like in the case of balancer.
    - refresh_balances may be set to True if the user's on-chain balances in some protocols has
    changed (for example if the user has deposited / withdrawn funds from a curve gauge).
    """
    matched_counterparty: Optional[str] = None
    refresh_balances: bool = False


DEFAULT_DECODING_OUTPUT: Final = DecodingOutput()
FAILED_ENRICHMENT_OUTPUT: Final = TransferEnrichmentOutput()
