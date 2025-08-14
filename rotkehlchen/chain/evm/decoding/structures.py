from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Final, Literal, NamedTuple, Optional

from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset, EvmToken
    from rotkehlchen.chain.evm.structures import EvmTxReceiptLog
    from rotkehlchen.fval import FVal
    from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
    from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
    from rotkehlchen.types import EvmTransaction


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class ActionItem:
    """Action items to propagate to other decoders during decoding"""
    action: Literal['transform', 'skip', 'skip & keep']
    from_event_type: 'HistoryEventType'
    from_event_subtype: 'HistoryEventSubType'
    asset: Optional['Asset'] = None
    amount: Optional['FVal'] = None
    location_label: str | None = None
    address: ChecksumEvmAddress | None = None
    to_event_type: Optional['HistoryEventType'] = None
    to_event_subtype: Optional['HistoryEventSubType'] = None
    to_notes: str | None = None
    to_counterparty: str | None = None
    to_product: 'EvmProduct | None' = None
    to_address: ChecksumEvmAddress | None = None
    to_location_label: str | None = None
    extra_data: dict | None = None
    # Optional events data that pairs them with the event of the action item
    # Contains a tuple with the paired event and whether it's an out event (True) or in event
    # This is a way to control the order of the action item generated event relative
    # to the paired events.
    paired_events_data: tuple[Sequence['EvmEvent'], bool] | None = None
    # if true adds the resulting transfer of the current action item to the next
    # action items paired event data. This is a way to guarantee order only via action items.
    pair_with_next_action_item: bool = False
    # Error tolerance that can be used for protocols having rounding errors. Such as with stETH (https://github.com/lidofinance/lido-dao/issues/442)
    # In those cases the notes should also be formatted to have an amount as format string since at
    # action item matching this format will populate the note with the actual amount
    amount_error_tolerance: Optional['FVal'] = None


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


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class DecodingOutput:
    """
    Output of decoding functions

    - events can be returned if the decoding method has generated new events and they needs to be
    added to the list of other decoded events.
    - action_items is a list of actions to be performed later automatically or to be passed
    in further decoding methods.
    - matched_counterparty is optionally set if needed for decoder rules that matched
    and is used in post-decoding rules like in the case of balancer
    - refresh_balances may be set to True if the user's on-chain balances in some protocols has
    changed (for example if the user has deposited / withdrawn funds from a curve gauge).
    - reload_decoders can be None in which case nothing happens. Or a set of decoders names for which to reload data. The decoder's name is the class name without the Decoder suffix. For example Eigenlayer for EigenlayerDecoder
    - process_swaps indicates whether there are swaps that need to be converted into EvmSwapEvents.
    """  # noqa: E501
    events: list['EvmEvent'] | None = None
    action_items: list[ActionItem] = field(default_factory=list)
    matched_counterparty: str | None = None
    refresh_balances: bool = False
    reload_decoders: set[str] | None = None
    process_swaps: bool = False


class TransferEnrichmentOutput(NamedTuple):
    """
    Return structure for the enrichment functions.

    - matched_counterparty is optionally set if needed for enrichment rules
    and is used in post-decoding rules like in the case of balancer.
    - refresh_balances may be set to True if the user's on-chain balances in some protocols has
    changed (for example if the user has deposited / withdrawn funds from a curve gauge).
    - process_swaps indicates whether there are swaps that need to be converted into EvmSwapEvents.
    """
    matched_counterparty: str | None = None
    refresh_balances: bool = False
    process_swaps: bool = False


DEFAULT_DECODING_OUTPUT: Final = DecodingOutput()
FAILED_ENRICHMENT_OUTPUT: Final = TransferEnrichmentOutput()
