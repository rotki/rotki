import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

from eth_typing import ChecksumAddress

from rotkehlchen.api.websockets.typedefs import WSMessageType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.arbitrum_one.constants import CPT_ARBITRUM_ONE
from rotkehlchen.chain.base.constants import CPT_BASE
from rotkehlchen.chain.base.modules.basenames.constants import CPT_BASENAMES
from rotkehlchen.chain.ethereum.airdrops import check_airdrops
from rotkehlchen.chain.ethereum.modules.ens.constants import CPT_ENS
from rotkehlchen.chain.evm.decoding.curve.constants import CPT_CURVE
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_AERODROME, CPT_VELODROME
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.constants import CPT_OPTIMISM
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
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_hex_color_code
from rotkehlchen.types import (
    ChainID,
    Location,
    OptionalBlockchainAddress,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
)
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now, ts_now_in_ms
from rotkehlchen.utils.mixins.customizable_date import CustomizableDateMixin

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
ENS_CALENDAR_COLOR: Final = deserialize_hex_color_code('5298FF')
CRV_CALENDAR_COLOR: Final = deserialize_hex_color_code('5bf054')
AERO_VELO_CALENDAR_COLOR: Final = deserialize_hex_color_code('36cfc9')
AIRDROP_CALENDAR_COLOR: Final = deserialize_hex_color_code('ffd966')
BRIDGE_CALENDAR_COLOR: Final = deserialize_hex_color_code('fcceee')

if TYPE_CHECKING:
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import HexColorCode


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=True)
class CalendarNotification(BaseReminderData):
    """Basic reminder information along the calendar event linked to it"""
    event: CalendarEntry

    def serialize(self) -> dict[str, Any]:
        return self.event.serialize() | {'reminder': super().serialize()}


def notify_reminders(
        reminders: dict[int, list[CalendarNotification]],
        database: DBHandler,
        msg_aggregator: MessagesAggregator,
) -> None:
    """Send websocket notifications for calendar reminders.

    The reminders dictionary maps each calendar event ID to a list of associated
    notifications, with the most recent reminder listed first.

    For events with multiple reminders, only the newest reminder (closest to event time)
    is processed and older ones are deleted. This ensures users don't get redundant
    notifications for the same event.
    """
    reminders_to_delete = []
    for event_reminders in reminders.values():
        if len(event_reminders) > 1:
            reminders_to_delete.extend([(r.identifier,) for r in event_reminders[1:]])

        msg_aggregator.add_message(
            message_type=WSMessageType.CALENDAR_REMINDER,
            data=event_reminders[0].serialize(),
        )

    with database.conn.write_ctx() as write_cursor:
        write_cursor.executemany(
            'DELETE FROM calendar_reminders WHERE identifier=?',
            reminders_to_delete,
        )


def delete_past_calendar_entries(database: DBHandler) -> None:
    """Delete past calendar events that are marked for auto-deletion,
    but only if all associated reminders (if any) have been acknowledged."""
    now = ts_now()
    with database.conn.write_ctx() as write_cursor:
        write_cursor.execute(
            'DELETE FROM calendar WHERE timestamp < ? AND auto_delete = 1 '
            'AND identifier IN (SELECT event_id FROM calendar_reminders WHERE acknowledged = 1);',
            (now,),
        )
        write_cursor.execute(  # remember last time this task ran
            'INSERT OR REPLACE INTO key_value_cache (name, value) VALUES (?, ?)',
            (DBCacheStatic.LAST_DELETE_PAST_CALENDAR_EVENTS.value, str(now)),
        )


class CalendarReminderCreator(CustomizableDateMixin):
    """Short-lived object used to create calendar reminders"""

    def __init__(self, database: DBHandler, current_ts: Timestamp):
        super().__init__(database=database)
        self.current_ts = current_ts
        self.db_calendar = DBCalendar(database=self.database)

        with self.database.conn.read_ctx() as cursor:
            self.blockchain_accounts = self.database.get_blockchain_accounts(cursor=cursor)

    def get_history_events(self, event_types: list[tuple[HistoryEventType, HistoryEventSubType]], counterparties: list[str]) -> list['EvmEvent']:  # noqa: E501
        """Get history events by event_type, event_subtype, and counterparty"""
        with self.database.conn.read_ctx() as cursor:
            return DBHistoryEvents(database=self.database).get_history_events(
                cursor=cursor,
                has_premium=True,  # not limiting here
                group_by_event_ids=False,
                filter_query=EvmEventFilterQuery.make(
                    and_op=True,
                    counterparties=counterparties,
                    type_and_subtype_combinations=event_types,
                ),
            )

    def get_existing_calendar_entry(
            self,
            name: str,
            counterparty: str,
            address: ChecksumAddress,
            blockchain: SupportedBlockchain,
    ) -> CalendarEntry | None:
        """Get calendar entries matching the given parameters.
        Returns a list of calendar entries or None if no entries match.
        """
        if (calendar_entries := self.db_calendar.query_calendar_entry(
                filter_query=CalendarFilterQuery.make(
                    and_op=True,
                    name=name,
                    addresses=[OptionalBlockchainAddress(
                        blockchain=blockchain,
                        address=address,
                    )],
                    blockchain=blockchain,
                    counterparty=counterparty,
                ),
        ))['entries_found'] == 0:  # if calendar entry doesn't exist, add it
            return None

        return calendar_entries['entries'][0]

    def create_or_update_calendar_entry(
            self,
            name: str,
            timestamp: Timestamp,
            description: str,
            counterparty: str,
            address: ChecksumAddress,
            blockchain: SupportedBlockchain,
            color: 'HexColorCode',
    ) -> int | None:
        """Create calendar entry if it doesn't exist.
        If it does exist, update it if the timestamp is different.
        Returns the id of the created entry or None if no entry was created.
        Also may return None in the case the entry was created but already has had a reminder set.
        """
        if (calendar_entry := self.get_existing_calendar_entry(
            name=name,
            counterparty=counterparty,
            address=address,
            blockchain=blockchain,
        )) is None:  # if calendar entry doesn't exist, add it
            return self.db_calendar.create_calendar_entry(CalendarEntry(
                name=name,
                timestamp=timestamp,
                description=description,
                counterparty=counterparty,
                address=address,
                blockchain=blockchain,
                color=color,
                auto_delete=True,
            ))

        # else calendar entry already exists
        if timestamp != calendar_entry.timestamp:  # update entry if timestamps don't match
            self.db_calendar.update_calendar_entry(CalendarEntry(
                identifier=calendar_entry.identifier,
                name=name,
                timestamp=timestamp,
                description=description,
                counterparty=counterparty,
                address=address,
                blockchain=blockchain,
                color=color,
                auto_delete=True,
            ))

        if self.db_calendar.count_reminder_entries(calendar_entry.identifier) > 0:
            return None  # already has a reminder entry so don't add any new ones

        return calendar_entry.identifier

    def create_or_update_calendar_entry_from_event(
            self,
            event: 'EvmEvent',
            name: str,
            description: str,
            timestamp: Timestamp,
            color: 'HexColorCode',
            counterparty: str,
    ) -> int | None:
        """Create calendar entry from an event.
        Returns the id of the created entry or None if no entry was created.
        Also may return None in the case the entry was created but already has had a reminder set.
        """
        assert event.location_label is not None
        if (
            (user_address := string_to_evm_address(event.location_label)) not in self.blockchain_accounts.get(  # noqa: E501
                blockchain := ChainID.deserialize(event.location.to_chain_id()).to_blockchain(),
            ) or timestamp <= self.current_ts
        ):
            return None  # Skip events in the past or from a different address

        return self.create_or_update_calendar_entry(
            name=name,
            timestamp=timestamp,
            description=description,
            counterparty=counterparty,
            address=user_address,
            blockchain=blockchain,
            color=color,
        )

    def delete_calendar_entry(
            self,
            name: str,
            counterparty: str,
            address: ChecksumAddress,
            blockchain: SupportedBlockchain,
    ) -> None:
        """Delete calendar entry and associated reminders if it exists"""
        if (calendar_entry := self.get_existing_calendar_entry(
            name=name,
            counterparty=counterparty,
            address=address,
            blockchain=blockchain,
        )) is None:
            return  # nothing to do if calendar entry doesn't exist

        try:
            self.db_calendar.delete_entry(
                identifier=calendar_entry.identifier,
                entry_type='calendar',
            )
            self.db_calendar.delete_entry(
                identifier=calendar_entry.identifier,
                entry_type='calendar_reminders',
            )
        except InputError as e:
            log.warning(f'Failed to remove calendar entry and reminders for {calendar_entry.name} due to {e!s}')  # noqa: E501

    def maybe_create_reminders(self, calendar_identifiers: list[int], secs_before: list[int], error_msg: str) -> None:  # noqa: E501
        _, failed_to_add = self.db_calendar.create_reminder_entries(reminders=[
            ReminderEntry(
                identifier=calendar_identifier,  # this is only used for logging below, it's auto generated in db  # noqa: E501
                event_id=calendar_identifier,
                secs_before=entry,
                acknowledged=False,
            )
            for calendar_identifier in calendar_identifiers
            for entry in secs_before
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
            counterparties=[CPT_ENS, CPT_BASENAMES],
        )) == 0:
            return

        ens_to_event: dict[str, tuple[int, EvmEvent]] = {}
        for ens_event in ens_events:
            if (
                not (extra_data := ens_event.extra_data or {}) or
                (ens_name := extra_data.get('name')) is None or
                (ens_expires := extra_data.get('expires')) is None or
                (counterparty := ens_event.counterparty) is None
            ):
                continue

            entry_id = self.create_or_update_calendar_entry_from_event(
                event=ens_event,
                name=f'{ens_name} expiry',
                timestamp=Timestamp(ens_expires),
                color=ENS_CALENDAR_COLOR,
                counterparty=counterparty,
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
            secs_before=[WEEK_IN_SECONDS, DAY_IN_SECONDS],
            error_msg='Failed to add the ENS expiry reminders',
        )

    def maybe_create_locked_crv_reminders(self) -> None:
        """Check for lock CRV in vote escrow history events and create reminders if needed."""
        if len(crv_events := self.get_history_events(
            event_types=[(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)],
            counterparties=[CPT_CURVE],
        )) == 0:
            return

        crv_calendar_entries: list[int] = []
        for crv_event in crv_events:
            if (
                not (extra_data := crv_event.extra_data or {}) or
                (locktime := extra_data.get('locktime')) is None
            ):
                continue

            entry_id = self.create_or_update_calendar_entry_from_event(
                event=crv_event,
                name='CRV vote escrow lock period ends',
                timestamp=Timestamp(locktime),
                color=CRV_CALENDAR_COLOR,
                counterparty=CPT_CURVE,
                description=f'Lock period for {crv_event.amount} CRV in vote escrow ends on {self.timestamp_to_date(locktime)}',  # noqa: E501
            )
            if entry_id is not None:
                crv_calendar_entries.append(entry_id)

        self.maybe_create_reminders(
            calendar_identifiers=crv_calendar_entries,
            secs_before=[0],
            error_msg='Failed to add the CRV lock period end reminders',
        )

    def maybe_create_locked_aero_vero_reminders(self) -> None:
        """Create reminders for AERO/VERO lock periods in vote escrow history events."""
        if len(events := self.get_history_events(
            event_types=[
                (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET),
                (HistoryEventType.INFORMATIONAL, HistoryEventSubType.NONE),  # unlock time updates
            ],
            counterparties=[CPT_VELODROME, CPT_AERODROME],
        )) == 0:
            return

        lock_entries: list[int] = []
        for event in events:
            if not (
                    event.extra_data is not None and
                    (lock_time := event.extra_data.get('lock_time')) is not None and
                    (token_id := event.extra_data.get('token_id')) is not None
            ):
                continue

            protocol_symbol = 'VELO' if event.counterparty == CPT_VELODROME else 'AERO'
            entry_id = self.create_or_update_calendar_entry_from_event(
                event=event,
                name=f'{protocol_symbol} veNFT-{token_id} vote escrow lock period ends',
                timestamp=Timestamp(lock_time),
                color=AERO_VELO_CALENDAR_COLOR,
                counterparty=event.counterparty,  # type: ignore[arg-type]  # counterparty is either velodrome or aerodrome
                description=f'Lock period for {protocol_symbol} veNFT-{token_id} in vote escrow ends on {self.timestamp_to_date(lock_time)}',  # noqa: E501
            )
            if entry_id is not None:
                lock_entries.append(entry_id)

        self.maybe_create_reminders(
            calendar_identifiers=lock_entries,
            secs_before=[0],
            error_msg='Failed to create reminders for VELO/AERO vote escrow lock expirations.',
        )

    def maybe_create_airdrop_claim_reminder(self) -> None:
        """Create reminders for airdrop claim deadlines."""
        with self.database.conn.read_ctx() as read_cursor:
            addresses = self.database.get_evm_accounts(read_cursor)

        data = check_airdrops(addresses=addresses, database=self.database)
        calendar_entries: list[int] = []
        for address, airdrops in data.items():
            for airdrop_name, airdrop_info in airdrops.items():
                if (
                        isinstance(airdrop_info, list) or  # for some it's a list of poaps. Ignore
                        (cutoff_time := airdrop_info.get('cutoff_time')) is None or
                        not isinstance(asset := airdrop_info.get('asset', None), EvmToken)
                ):
                    continue  # not an airdrop to set a reminder for

                pretty_name = airdrop_name.replace('_', ' ').capitalize()
                entry_name = f'{pretty_name} airdrop claim deadline'

                # TODO: Add zksync era to SupportedBlockchain - https://github.com/orgs/rotki/projects/11/views/2?pane=issue&itemId=81788541  # noqa: E501
                if asset.chain_id == ChainID.ZKSYNC_ERA:
                    continue  # Skip airdrops on zksync era

                blockchain = asset.chain_id.to_blockchain()
                if address not in self.blockchain_accounts.get(blockchain):
                    continue  # skip if address hasn't been added to this chain in rotki

                if (
                    airdrop_info.get('claimed', False) is True or
                    cutoff_time <= ts_now()
                ):  # Delete any existing entry if already claimed, unknown cutoff, or past cutoff
                    self.delete_calendar_entry(
                        name=entry_name,
                        counterparty=airdrop_name,
                        address=address,
                        blockchain=blockchain,
                    )
                    continue  # skip trying to create or update anything

                entry_id = self.create_or_update_calendar_entry(
                    name=entry_name,
                    timestamp=cutoff_time,
                    description=f"{pretty_name} airdrop of {airdrop_info.get('amount', 0)} {asset.symbol_or_name()} has claim deadline on {self.timestamp_to_date(cutoff_time)}",  # noqa: E501
                    counterparty=airdrop_name,
                    address=address,
                    blockchain=blockchain,
                    color=AIRDROP_CALENDAR_COLOR,
                )
                if entry_id is not None:
                    calendar_entries.append(entry_id)

        self.maybe_create_reminders(
            calendar_identifiers=calendar_entries,
            secs_before=[WEEK_IN_SECONDS, DAY_IN_SECONDS],
            error_msg='Failed to add the airdrop claim reminders',
        )

    def maybe_create_l2_bridging_reminder(self) -> None:
        """Creates calendar reminders for L2 bridge claims (7 days after deposit).
        Tracks deposits on Base, Optimism, and Arbitrum networks.
        """
        bridge_events: list[EvmEvent] = []
        locations_to_counterparties = (
            (Location.BASE, CPT_BASE),
            (Location.OPTIMISM, CPT_OPTIMISM),
            (Location.ARBITRUM_ONE, CPT_ARBITRUM_ONE),
        )
        db_history_events = DBHistoryEvents(database=self.database)
        with self.database.conn.read_ctx() as cursor:
            for location, counterparty in locations_to_counterparties:
                bridge_events.extend(db_history_events.get_history_events(
                    cursor=cursor,
                    has_premium=True,
                    filter_query=EvmEventFilterQuery.make(
                        and_op=True,
                        location=location,
                        counterparties=[counterparty],
                        event_types=[HistoryEventType.DEPOSIT],
                        event_subtypes=[HistoryEventSubType.BRIDGE],
                    ),
                ))

        now = ts_now_in_ms()
        bridge_calendar_entries: list[int] = []
        for bridge_event in bridge_events:
            if now - bridge_event.timestamp > WEEK_IN_SECONDS * 1000:
                continue

            try:
                asset_symbol = bridge_event.asset.resolve_to_asset_with_symbol().symbol
                if (entry_id := self.create_or_update_calendar_entry_from_event(
                        name=f'Claim {bridge_event.amount} {asset_symbol} bridge deposit on Ethereum',  # noqa: E501
                        event=bridge_event,
                        color=BRIDGE_CALENDAR_COLOR,
                        counterparty=bridge_event.counterparty,  # type: ignore[arg-type]  # counterparty is always present
                        timestamp=ts_ms_to_sec(TimestampMS(bridge_event.timestamp + WEEK_IN_SECONDS * 1000)),  # noqa: E501
                        description=f'Bridge deposit of {bridge_event.amount} {asset_symbol} is ready to claim on Ethereum',  # noqa: E501
                )) is not None:
                    bridge_calendar_entries.append(entry_id)
            except UnknownAsset:
                log.exception(f'Unable to add reminder for bridge event with hash {bridge_event.tx_hash.hex()} on {bridge_event.location.name}')  # noqa: E501
                continue

        self.maybe_create_reminders(
            secs_before=[0],
            calendar_identifiers=bridge_calendar_entries,
            error_msg='Failed to add the bridge claim reminders',
        )


def maybe_create_calendar_reminders(database: DBHandler) -> None:
    """Create all needed calendar reminders"""
    current_ts = ts_now()
    reminder_creator = CalendarReminderCreator(database=database, current_ts=current_ts)
    reminder_creator.maybe_create_ens_reminders()
    reminder_creator.maybe_create_locked_crv_reminders()
    reminder_creator.maybe_create_locked_aero_vero_reminders()
    reminder_creator.maybe_create_airdrop_claim_reminder()
    reminder_creator.maybe_create_l2_bridging_reminder()

    with database.conn.write_ctx() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.LAST_CREATE_REMINDER_CHECK_TS,
            value=current_ts,
        )
