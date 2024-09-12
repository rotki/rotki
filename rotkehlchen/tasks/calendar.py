import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.ethereum.modules.ens.constants import CPT_ENS
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.timing import DAY_IN_SECONDS, WEEK_IN_SECONDS
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.calendar import (
    BaseReminderData,
    CalendarEntry,
    CalendarFilterQuery,
    DBCalendar,
    ReminderEntry,
)
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_hex_color_code
from rotkehlchen.types import ChainID, OptionalBlockchainAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
ENS_CALENDAR_COLOR: Final = deserialize_hex_color_code('5298FF')
CRV_CALENDAR_COLOR: Final = deserialize_hex_color_code('5bf054')

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import HexColorCode


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class CalendarNotification(BaseReminderData):
    """Basic reminder information along the calendar event linked to it"""
    event: CalendarEntry

    def serialize(self) -> dict[str, str | int]:
        return self.event.serialize()


def notify_reminders(
        reminders: list[CalendarNotification],
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
) -> None:
    """Send a ws notification for the calendar reminders and delete them once processed"""
    notified_events = set()
    for reminder in reminders:
        if reminder.event.identifier in notified_events:
            continue  # avoid sending notifications for the same event multiple times

        msg_aggregator.add_message(
            message_type=WSMessageType.CALENDAR_REMINDER,
            data=reminder.serialize(),
        )
        notified_events.add(reminder.event.identifier)

    with database.conn.write_ctx() as write_cursor:
        write_cursor.executemany(
            'DELETE FROM calendar_reminders WHERE identifier=?',
            [(event.identifier,) for event in reminders],
        )


def delete_past_calendar_entries(database: DBHandler) -> None:
    """delete old calendar entries that the user has allowed to delete"""
    with database.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'DELETE FROM calendar WHERE timestamp < ? AND auto_delete=1',
            (ts_now(),),
        )


class CalendarReminderCreator(CustomizableDateMixin):
    """Short-lived object used to create calendar reminders"""

    def __init__(self, database: DBHandler, current_ts: Timestamp):
        super().__init__(database=database)
        self.current_ts = current_ts
        self.db_calendar = DBCalendar(database=self.database)

        with self.database.conn.read_ctx() as cursor:
            self.blockchain_accounts = self.database.get_blockchain_accounts(cursor=cursor)

    def get_history_events(self, event_types: list[tuple[HistoryEventType, HistoryEventSubType]], counterparty: str) -> list['EvmEvent']:  # noqa: E501
        """Get history events by event_type, event_subtype, and counterparty"""
        db_history_events = DBHistoryEvents(database=self.database)
        events: list[EvmEvent] = []
        with self.database.conn.read_ctx() as cursor:
            for event_type, event_subtype in event_types:
                events.extend(db_history_events.get_history_events(
                    cursor=cursor,
                    has_premium=True,  # not limiting here
                    group_by_event_ids=False,
                    filter_query=EvmEventFilterQuery.make(
                        and_op=True,
                        counterparties=[counterparty],
                        event_types=[event_type],
                        event_subtypes=[event_subtype],
                    ),
                ))

        return events

    def maybe_create_calendar_entry(self, event: 'EvmEvent', name: str, description: str, timestamp: Timestamp, color: 'HexColorCode', counterparty: str) -> int | None:  # noqa: E501
        """Create calendar entry from an event.
        Returns the id of the entry created or None if no entry was created"""
        assert event.location_label is not None
        if (
            (user_address := string_to_evm_address(event.location_label)) not in self.blockchain_accounts.get(  # noqa: E501
                blockchain := ChainID.deserialize(event.location.to_chain_id()).to_blockchain(),
            ) or timestamp <= self.current_ts
        ):
            return None  # Skip events in the past or from a different address

        if (calendar_entries := self.db_calendar.query_calendar_entry(
                filter_query=CalendarFilterQuery.make(
                    and_op=True,
                    name=name,
                    addresses=[OptionalBlockchainAddress(
                        blockchain=blockchain,
                        address=user_address,
                    )],
                    blockchain=blockchain,
                    counterparty=counterparty,
                ),
        ))['entries_found'] == 0:  # if calendar entry doesn't exist, add it
            entry_id = self.db_calendar.create_calendar_entry(CalendarEntry(
                name=name,
                timestamp=timestamp,
                description=description,
                counterparty=counterparty,
                address=user_address,
                blockchain=blockchain,
                color=color,
                auto_delete=True,
            ))
        else:  # else calendar entry already exists
            calendar_entry = calendar_entries['entries'][0]
            if timestamp > calendar_entry.timestamp:  # if a later expiry is found
                self.db_calendar.update_calendar_entry(CalendarEntry(
                    identifier=calendar_entry.identifier,
                    name=name,
                    timestamp=timestamp,  # update the calendar entry
                    description=description,
                    counterparty=counterparty,
                    address=user_address,
                    blockchain=blockchain,
                    color=color,
                    auto_delete=True,
                ))

            if self.db_calendar.count_reminder_entries(
                    event_id=(entry_id := calendar_entry.identifier),
            ) > 0:  # already has a reminder entry
                return None  # we don't add any new automatic reminders

        return entry_id

    def maybe_create_reminders(self, calendar_identifiers: list[int], secs_befores: list[int], error_msg: str) -> None:  # noqa: E501
        _, failed_to_add = self.db_calendar.create_reminder_entries(reminders=[
            ReminderEntry(
                identifier=calendar_identifier,  # this is only used for logging below, it's auto generated in db  # noqa: E501
                event_id=calendar_identifier,
                secs_before=secs_before,
            )
            for calendar_identifier in calendar_identifiers
            for secs_before in secs_befores
        ])

        if len(failed_to_add) == 0:
            return

        log.error(  # failed_to_add is a list of calendar_identifier that were passed as identifiers of reminder entry above  # noqa: E501
            f"""{error_msg} for {', '.join([
                entry.name for entry in self.db_calendar.query_calendar_entry(
                    CalendarFilterQuery.make(identifiers=failed_to_add)
                )['entries']
            ])}""",
        )

    def maybe_create_ens_reminders(self) -> None:
        """Check ENS registration and renewal history events and create reminders if needed."""
        if len(ens_events := self.get_history_events(
            event_types=[
                (HistoryEventType.TRADE, HistoryEventSubType.SPEND),
                (HistoryEventType.RENEW, HistoryEventSubType.NONE),
            ],
            counterparty=CPT_ENS,
        )) == 0:
            return

        ens_to_event: dict[str, tuple[int, EvmEvent]] = {}
        for ens_event in ens_events:
            if (
                not (extra_data := ens_event.extra_data or {}) or
                (ens_name := extra_data.get('name')) is None or
                (ens_expires := extra_data.get('expires')) is None
            ):
                continue

            entry_id = self.maybe_create_calendar_entry(
                event=ens_event,
                name=f'{ens_name} expiry',
                timestamp=Timestamp(ens_expires),
                color=ENS_CALENDAR_COLOR,
                counterparty=CPT_ENS,
                description=f'{ens_name} expires on {self.timestamp_to_date(ens_expires)}',
            )

            if (
                entry_id is not None and (
                    ens_name not in ens_to_event or
                    ens_expires > ens_to_event[ens_name][1].extra_data['expires']  # type: ignore[index]  # extra_data is not None, checked above
                )
            ):  # insert mapping for the latest expiry timestamp
                ens_to_event[ens_name] = (entry_id, ens_event)

        self.maybe_create_reminders(
            calendar_identifiers=[t[0] for t in ens_to_event.values()],
            secs_befores=[WEEK_IN_SECONDS, DAY_IN_SECONDS],
            error_msg='Failed to add the ENS expiry reminders',
        )

    def maybe_create_locked_crv_reminders(self) -> None:
        """Check for lock CRV in vote escrow history events and create reminders if needed."""
        if len(crv_events := self.get_history_events(
            event_types=[(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)],
            counterparty=CPT_CURVE,
        )) == 0:
            return

        crv_calendar_entries: list[int] = []
        for crv_event in crv_events:
            if (
                not (extra_data := crv_event.extra_data or {}) or
                (locktime := extra_data.get('locktime')) is None
            ):
                continue

            entry_id = self.maybe_create_calendar_entry(
                event=crv_event,
                name='CRV vote escrow lock period ends',
                timestamp=Timestamp(locktime),
                color=CRV_CALENDAR_COLOR,
                counterparty=CPT_CURVE,
                description=f'Lock period for {crv_event.balance.amount} CRV in vote escrow ends on {self.timestamp_to_date(locktime)}',  # noqa: E501
            )
            if entry_id is not None:
                crv_calendar_entries.append(entry_id)

        self.maybe_create_reminders(
            calendar_identifiers=crv_calendar_entries,
            secs_befores=[0],
            error_msg='Failed to add the CRV lock period end reminders',
        )


def maybe_create_calendar_reminders(database: DBHandler) -> None:
    """Create all needed calendar reminders"""
    current_ts = ts_now()
    reminder_creator = CalendarReminderCreator(database=database, current_ts=current_ts)
    reminder_creator.maybe_create_ens_reminders()
    reminder_creator.maybe_create_locked_crv_reminders()

    with database.conn.write_ctx() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_CREATE_REMINDER_CHECK_TS,
            value=current_ts,
        )
