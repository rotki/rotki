from dataclasses import dataclass

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.db.calendar import BaseReminderData, CalendarEntry
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_now


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
