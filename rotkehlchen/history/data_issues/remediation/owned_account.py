from typing import TYPE_CHECKING, Final, Protocol, TypeGuard

from rotkehlchen.db.filtering import HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.data_issues.constants import IssueKind
from rotkehlchen.history.data_issues.remediation.base import (
    BaseRemediationStrategy,
    RemediationOutcome,
)
from rotkehlchen.history.events.structures.onchain_event import OnchainEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.serialization.deserialize import deserialize_int
from rotkehlchen.tasks.historical_balances import process_historical_balances
from rotkehlchen.types import (
    BLOCKCHAIN_LOCATIONS,
    BLOCKCHAIN_LOCATIONS_TYPE,
    CHAINS_WITH_TRANSACTIONS,
    Location,
    SupportedBlockchain,
    TimestampMS,
    TuplesOfBlockchainAddresses,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.history.data_issues.types import DataIssue
    from rotkehlchen.user_messages import MessagesAggregator


class ChainsAggregatorWithActiveAddresses(Protocol):
    def get_active_addresses(
            self,
            blockchain: SupportedBlockchain,
    ) -> TuplesOfBlockchainAddresses:
        ...


INTERNAL_TRANSFER_TYPE: Final = HistoryEventType.TRANSACTION_TO_SELF
INTERNAL_TRANSFER_SUBTYPE: Final = HistoryEventSubType.NONE


def _is_blockchain_location(location: Location) -> TypeGuard[BLOCKCHAIN_LOCATIONS_TYPE]:
    return location in BLOCKCHAIN_LOCATIONS


class OwnedAccountCounterpartyStrategy(BaseRemediationStrategy):
    """Reclassify an onchain spend as internal if the counterparty is tracked."""

    name: Final = 'owned_account_counterparty'
    timeout: int = 5

    def __init__(
            self,
            database: 'DBHandler',
            chains_aggregator: ChainsAggregatorWithActiveAddresses,
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        self.database = database
        self.chains_aggregator = chains_aggregator
        self.msg_aggregator = msg_aggregator
        self._applicable_issues: dict[int, tuple[SupportedBlockchain, OnchainEvent]] = {}

    def _get_chain(self, issue: 'DataIssue') -> SupportedBlockchain | None:
        try:
            location = Location.deserialize_from_db(issue.location)
        except DeserializationError:
            return None

        if not _is_blockchain_location(location):
            return None

        chain = SupportedBlockchain.from_location(location)
        return chain if chain in CHAINS_WITH_TRANSACTIONS else None

    def _get_event(self, issue: 'DataIssue') -> OnchainEvent | None:
        if (raw_event_identifier := issue.payload.get('event_identifier')) is None:
            return None
        try:
            event_identifier = deserialize_int(
                value=raw_event_identifier,
                location='data issue event identifier',
            )
        except DeserializationError:
            return None

        with self.database.conn.read_ctx() as cursor:
            events = DBHistoryEvents(self.database).get_history_events_internal(
                cursor=cursor,
                filter_query=HistoryEventFilterQuery.make(identifiers=[event_identifier]),
            )
        if len(events) != 1 or not isinstance(event := events[0], OnchainEvent):
            return None

        return event

    def applies_to(self, issue: 'DataIssue') -> bool:
        self._applicable_issues.pop(issue.id, None)
        if issue.kind != IssueKind.NEGATIVE_BALANCE or (chain := self._get_chain(issue)) is None:
            return False
        if (event := self._get_event(issue)) is None or event.address is None:
            return False
        if (event.event_type, event.event_subtype) == (
            INTERNAL_TRANSFER_TYPE,
            INTERNAL_TRANSFER_SUBTYPE,
        ):
            return False

        self._applicable_issues[issue.id] = (chain, event)
        return True

    def attempt(self, issue: 'DataIssue') -> RemediationOutcome:
        if (cached_data := self._applicable_issues.pop(issue.id, None)) is None:
            chain = self._get_chain(issue)
            event = self._get_event(issue)
            if chain is None or event is None:
                return RemediationOutcome(
                    False,
                    'event_not_resolvable',
                    'Event or chain could not be resolved',
                )
        else:
            chain, event = cached_data

        if event.address is None:
            return RemediationOutcome(
                False,
                'counterparty_unknown',
                'Event has no counterparty address',
            )

        counterparty = str(event.address)
        active_addresses = {
            str(address) for address in self.chains_aggregator.get_active_addresses(chain)
        }
        if counterparty not in active_addresses:
            return RemediationOutcome(
                resolved=False,
                attribution='counterparty_not_owned',
                notes=f'{counterparty} is not tracked on {chain!s}',
            )

        assert event.identifier is not None, 'Persisted event should have an identifier'
        notes = f'Reclassified as internal transfer to owned {chain!s} account {counterparty}'
        with self.database.user_write() as write_cursor:
            DBHistoryEvents(self.database).update_events_and_track(
                write_cursor=write_cursor,
                where_clause='WHERE identifier=?',
                where_bindings=(event.identifier,),
                set_clause='SET type=?, subtype=?, notes=?',
                set_bindings=(
                    INTERNAL_TRANSFER_TYPE.serialize(),
                    INTERNAL_TRANSFER_SUBTYPE.serialize(),
                    notes,
                ),
            )
        process_historical_balances(
            database=self.database,
            msg_aggregator=self.msg_aggregator,
            from_ts=TimestampMS(issue.ts_start),
        )
        return RemediationOutcome(
            resolved=True,
            attribution='reclassified_as_internal_transfer',
            notes=f'Counterparty {counterparty} on {chain!s} is tracked by the user',
        )
