import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.chain.ethereum.modules.ens.constants import CPT_ENS
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
from rotkehlchen.types import ChainID, OptionalBlockchainAddress, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.evm_event import EvmEvent


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


def maybe_create_ens_reminders(database: DBHandler) -> None:
    """Check ENS registration and renewal history events and create reminders if needed."""
    db_history_events = DBHistoryEvents(database=database)
    ens_events: list['EvmEvent'] = []
    with database.conn.read_ctx() as cursor:
        for event_type, event_subtype in (
            (HistoryEventType.TRADE, HistoryEventSubType.SPEND),
            (HistoryEventType.RENEW, HistoryEventSubType.NONE),
        ):
            ens_events.extend(db_history_events.get_history_events(
                cursor=cursor,
                has_premium=True,  # not limiting here
                group_by_event_ids=False,
                filter_query=EvmEventFilterQuery.make(
                    and_op=True,
                    counterparties=[CPT_ENS],
                    event_types=[event_type],
                    event_subtypes=[event_subtype],
                ),
            ))

    if len(ens_events) == 0:
        return

    db_calendar = DBCalendar(database=database)
    customizable_date = CustomizableDateMixin(database=database)
    with database.conn.read_ctx() as cursor:
        blockchain_accounts = database.get_blockchain_accounts(cursor=cursor)

    current_ts = ts_now()
    ens_to_event: dict[str, tuple[int, EvmEvent]] = {}
    for ens_event in ens_events:
        if not (
            ens_event.location_label is not None and
            ens_event.extra_data is not None and
            (ens_name := ens_event.extra_data.get('name')) is not None and
            (ens_expires := ens_event.extra_data.get('expires')) is not None and (
                user_address := string_to_evm_address(ens_event.location_label)
            ) in blockchain_accounts.get(
                blockchain := ChainID.deserialize(ens_event.location.to_chain_id()).to_blockchain(),  # noqa: E501
            ) and (ens_expires := Timestamp(ens_expires)) > current_ts  # those with expiry in the future  # noqa: E501
        ):
            continue

        calendar_entry_description = f'{ens_name} expires on {customizable_date.timestamp_to_date(ens_expires)}'  # noqa: E501
        if (calendar_entries := db_calendar.query_calendar_entry(
            filter_query=CalendarFilterQuery.make(
                and_op=True,
                name=f'{ens_name} expiry',
                addresses=[OptionalBlockchainAddress(
                    blockchain=blockchain,
                    address=user_address,
                )],
                blockchain=blockchain,
                counterparty=CPT_ENS,
            ),
        ))['entries_found'] == 0:  # if calendar entry doesn't exist, add it
            calendar_entry_id = db_calendar.create_calendar_entry(CalendarEntry(
                name=f'{ens_name} expiry',
                timestamp=ens_expires,
                description=calendar_entry_description,
                counterparty=CPT_ENS,
                address=user_address,
                blockchain=blockchain,
                color=None,
                auto_delete=True,
            ))
        else:  # else calendar entry already exists
            calendar_entry = calendar_entries['entries'][0]
            if ens_expires > calendar_entry.timestamp:  # if a later expiry is found
                db_calendar.update_calendar_entry(CalendarEntry(
                    identifier=calendar_entry.identifier,
                    name=f'{ens_name} expiry',
                    timestamp=ens_expires,  # update the calendar entry
                    description=calendar_entry_description,
                    counterparty=CPT_ENS,
                    address=user_address,
                    blockchain=blockchain,
                    color=None,
                    auto_delete=True,
                ))

            if db_calendar.count_reminder_entries(
                event_id=(calendar_entry_id := calendar_entry.identifier),
            ) > 0:  # already has a reminder entry
                continue  # we don't add any new automatic reminders

        if (
            ens_name not in ens_to_event or
            ens_expires > ens_to_event[ens_name][1].extra_data['expires']  # type: ignore[index]  # extra_data is not None, checked above
        ):  # insert mapping for the latest expiry timestamp
            ens_to_event[ens_name] = (calendar_entry_id, ens_event)

    _, failed_to_add = db_calendar.create_reminder_entries(reminders=[
        ReminderEntry(
            identifier=calendar_identifier,  # this is only used for logging below, it's auto generated in db  # noqa: E501
            event_id=calendar_identifier,
            secs_before=secs_before,
        )
        for calendar_identifier, _ in ens_to_event.values()
        for secs_before in (WEEK_IN_SECONDS, DAY_IN_SECONDS)
    ])

    with database.conn.write_ctx() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_CREATE_REMINDER_CHECK_TS,
            value=current_ts,
        )

    if len(failed_to_add) == 0:
        return

    log.error(  # failed_to_add is a list of calendar_identifier that were passed as identifiers of reminder entry above  # noqa: E501
        f"""Failed to add the ENS expiry reminders for {', '.join([
            entry.name for entry in db_calendar.query_calendar_entry(CalendarFilterQuery.make(
                identifiers=failed_to_add,
            ))['entries']
        ])}""",
    )
