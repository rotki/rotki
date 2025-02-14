import logging
from typing import TYPE_CHECKING, Any, Literal, NotRequired, TypedDict

from rotkehlchen.accounting.mixins.event import AccountingEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.location_details import get_formatted_location_name
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import hash_id
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import (
    HISTORY_EVENT_DB_TUPLE_WRITE,
    HistoryBaseEntry,
    HistoryBaseEntryType,
)
from rotkehlchen.history.events.structures.types import (
    HistoryEventSubType,
    HistoryEventType,
)
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import Location, TimestampMS
from rotkehlchen.utils.misc import ts_ms_to_sec

if TYPE_CHECKING:
    from more_itertools import peekable

    from rotkehlchen.accounting.mixins.event import AccountingEventMixin
    from rotkehlchen.accounting.pot import AccountingPot
    from rotkehlchen.types import Fee

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AssetMovementExtraData(TypedDict):
    """Typed dict with all the valid fields used in extra_data for AssetMovements"""
    # Address receiving or sending funds in the asset movement.
    address: NotRequired[str]
    # Transaction if it is available where funds were moved on chain.
    transaction_id: NotRequired[str]
    # Internal reference used in exchanges.
    reference: NotRequired[str]
    # Internal use only. Used for matching the corresponding crypto_transaction. Removed before being saved to the DB.  # noqa: E501
    fee: NotRequired['Fee']
    # blockchain where the transaction happened. We use string since
    # it can be a non supported blockchain
    blockchain: NotRequired[str]


class AssetMovement(HistoryBaseEntry[AssetMovementExtraData | None]):
    """Asset movement event representing deposits and withdrawals on exchanges."""

    extra_data: AssetMovementExtraData | None

    def __init__(
            self,
            timestamp: TimestampMS,
            location: Location,
            event_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL],
            asset: Asset,
            amount: FVal,
            identifier: int | None = None,
            event_identifier: str | None = None,
            unique_id: str | None = None,
            extra_data: AssetMovementExtraData | None = None,
            is_fee: bool = False,
            location_label: str | None = None,
    ) -> None:
        """
        `unique_id`: Unique identifier for this asset movement.
            Either the exchange transaction id or the associated onchain transaction hash.
            Used in conjunction with location to generate the event identifier.
        `is_fee`: Controls whether this represents a fee event.
        """
        location_name = get_formatted_location_name(location)
        asset_symbol = asset.resolve_to_asset_with_symbol().symbol
        if is_fee:
            sequence_index = 1
            event_subtype = HistoryEventSubType.FEE
            notes = f'Pay {amount} {asset_symbol} as {location_name} {str(event_type).lower()} fee'
        else:
            sequence_index = 0
            if event_type == HistoryEventType.DEPOSIT:
                event_subtype = HistoryEventSubType.DEPOSIT_ASSET
                notes = f'Deposit {amount} {asset_symbol} to {location_name}'
            else:
                event_subtype = HistoryEventSubType.REMOVE_ASSET
                notes = f'Withdraw {amount} {asset_symbol} from {location_name}'

        super().__init__(
            event_identifier=event_identifier if event_identifier is not None else self._create_event_identifier(  # noqa: E501
                location=location,
                timestamp=timestamp,
                asset=asset,
                amount=amount,
                unique_id=unique_id,
            ),
            sequence_index=sequence_index,
            timestamp=timestamp,
            location=location,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=asset,
            amount=amount,
            notes=notes,
            identifier=identifier,
            extra_data=extra_data,
            location_label=location_label,
        )

    @staticmethod
    def _create_event_identifier(
            location: Location,
            timestamp: TimestampMS,
            asset: Asset,
            amount: FVal,
            unique_id: str | None,
    ) -> str:
        """Create a unique event identifier from the given parameters.
        `unique_id` is a transaction id from the exchange, which in combination with the
        location makes a unique event identifier. If this is not available, the location,
        timestamp, asset, and balance must all be combined to ensure a unique identifier.
        """
        if unique_id is not None:
            return hash_id(str(location) + unique_id)

        return hash_id(
            str(location) +
            str(timestamp) +
            asset.identifier +
            str(amount),
        )

    @property
    def entry_type(self) -> HistoryBaseEntryType:
        return HistoryBaseEntryType.ASSET_MOVEMENT_EVENT

    def serialize_for_db(self) -> tuple[tuple[str, str, HISTORY_EVENT_DB_TUPLE_WRITE]]:
        return (self._serialize_base_tuple_for_db(),)

    @classmethod
    def deserialize_from_db(cls: type['AssetMovement'], entry: tuple) -> 'AssetMovement':
        """Deserialize an AssetMovement DB tuple.
        May raise:
        - DeserializationError
        - UnknownAsset
        """
        amount = deserialize_fval(entry[7], 'amount', 'asset movement event')
        return cls(
            identifier=entry[0],
            event_identifier=entry[1],
            timestamp=TimestampMS(entry[3]),
            location=Location.deserialize_from_db(entry[4]),
            location_label=entry[5],
            event_type=HistoryEventType.deserialize(entry[9]),  # type: ignore  # should always be correct from the DB
            is_fee=(HistoryEventSubType.deserialize(entry[10]) == HistoryEventSubType.FEE),
            asset=Asset(entry[6]).check_existence(),
            amount=amount,
            extra_data=cls.deserialize_extra_data(entry=entry, extra_data=entry[11]),
        )

    @classmethod
    def deserialize(cls: type['AssetMovement'], data: dict[str, Any]) -> 'AssetMovement':
        base_data = cls._deserialize_base_history_data(data)
        if (event_type := base_data['event_type']) not in {
            HistoryEventType.DEPOSIT,
            HistoryEventType.WITHDRAWAL,
        }:
            raise DeserializationError(
                f'Unsupported asset movement event type {event_type}. '
                f'Expected DEPOSIT or WITHDRAWAL',
            )

        return cls(
            identifier=base_data['identifier'],
            event_identifier=base_data['event_identifier'],
            timestamp=base_data['timestamp'],
            location=base_data['location'],
            location_label=base_data['location_label'],
            event_type=event_type,  # type: ignore  # just confirmed it's a DEPOSIT or WITHDRAWAL above
            is_fee=(base_data['event_subtype'] == HistoryEventSubType.FEE),
            asset=base_data['asset'],
            amount=base_data['amount'],
            extra_data=base_data['extra_data'],
        )

    def __repr__(self) -> str:
        return f'AssetMovement({", ".join(self._history_base_entry_repr_fields())})'

    # -- Methods of AccountingEventMixin

    @staticmethod
    def get_accounting_event_type() -> AccountingEventType:
        return AccountingEventType.ASSET_MOVEMENT

    def process(
            self,
            accounting: 'AccountingPot',
            events_iterator: "peekable['AccountingEventMixin']",  # pylint: disable=unused-argument
    ) -> int:
        if self.asset.identifier == 'KFEE' or self.amount == ZERO:
            # There is no reason to process deposits of KFEE for kraken as it has only value
            # internal to kraken and KFEE has no value and will error at cryptocompare price query.
            return 1

        if self.event_subtype == HistoryEventSubType.FEE:
            accounting.add_out_event(
                originating_event_id=self.identifier,
                event_type=AccountingEventType.ASSET_MOVEMENT,
                notes=self.notes if self.notes is not None else '',
                location=self.location,
                timestamp=ts_ms_to_sec(self.timestamp),
                asset=self.asset,
                amount=self.amount,
                taxable=True,
                count_entire_amount_spend=True,
                count_cost_basis_pnl=True,
            )

        return 1


def create_asset_movement_with_fee(
        timestamp: TimestampMS,
        location: Location,
        event_type: Literal[HistoryEventType.DEPOSIT, HistoryEventType.WITHDRAWAL],
        asset: Asset,
        amount: 'FVal',
        fee_asset: Asset,
        fee: 'FVal',
        location_label: str | None = None,
        unique_id: str | None = None,
        identifier: int | None = None,
        fee_identifier: int | None = None,
        extra_data: AssetMovementExtraData | None = None,
) -> list[AssetMovement]:
    """Create an asset movement and its corresponding fee event.
    Returns the new asset movements in a list.
    """
    events = [AssetMovement(
        location=location,
        event_type=event_type,
        timestamp=timestamp,
        asset=asset,
        amount=amount,
        unique_id=unique_id,
        identifier=identifier,
        extra_data=extra_data,
        location_label=location_label,
    )]
    if fee != ZERO:
        events.append(AssetMovement(
            identifier=fee_identifier,
            event_identifier=events[0].event_identifier,
            location=location,
            event_type=event_type,
            timestamp=timestamp,
            asset=fee_asset,
            amount=fee,
            is_fee=True,
            location_label=location_label,
        ))

    return events
