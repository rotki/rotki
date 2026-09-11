"""The bank connector base class.

A bank is registered, stored, balance-queried and history-synced through the exchange
plumbing: same credential table, same manager, same API endpoints, same history event
pipeline. What a connector adds on top is the manifest, the normalized transaction model
with its cursor-based incremental sync, session persistence hooks and the error taxonomy.

A connector implements `query_accounts` and `query_transactions`. Everything else is
generic.
"""
import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import TYPE_CHECKING, Any, ClassVar

from rotkehlchen.banks.errors import BankAuthExpired, BankError
from rotkehlchen.banks.normalization import (
    BankAccount,
    BankTransaction,
    bank_transaction_to_events,
)
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.exchanges.exchange import ExchangeInterface, ExchangeQueryBalances
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ApiKey, ApiSecret, Timestamp
from rotkehlchen.utils.mixins.cacheable import cache_response_timewise
from rotkehlchen.utils.mixins.lockable import protect_with_lock

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from rotkehlchen.assets.asset import AssetWithOracles
    from rotkehlchen.banks.manifest import BankManifest
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.exchanges.data_structures import MarginPosition
    from rotkehlchen.exchanges.exchange import HistoryEventQueue
    from rotkehlchen.history.events.structures.base import HistoryBaseEntry
    from rotkehlchen.user_messages import MessagesAggregator

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BankConnector(ExchangeInterface, ABC):
    manifest: ClassVar[BankManifest]
    # Re-fetch this much before the persisted cursor on every sync. Covers clock skew and
    # late edits at the bank. Overlap is harmless: events dedup on their source id.
    cursor_safety_window: ClassVar[int] = DAY_IN_SECONDS

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            database: DBHandler,
            msg_aggregator: MessagesAggregator,
    ) -> None:
        super().__init__(
            name=name,
            location=self.manifest.location,
            api_key=api_key,
            secret=secret,
            database=database,
            msg_aggregator=msg_aggregator,
        )

    # ---- what a connector implements ----

    @abstractmethod
    def query_accounts(self) -> list[BankAccount]:
        """Query the bank for the accounts the credentials can see, with settled balances.

        May raise BankError (or any RemoteError) on failure.
        """

    @abstractmethod
    def query_transactions(
            self,
            account: BankAccount,
            updated_since: Timestamp | None,
    ) -> list[BankTransaction]:
        """Query the final transactions of one account.

        `updated_since` is None on a full sync. Otherwise the connector fetches everything
        the bank modified at or after it, which includes transactions that became final
        since the last sync. The framework already subtracted the safety window.

        May raise BankError (or any RemoteError) on failure.
        """

    # ---- session persistence hooks ----
    # Connectors whose auth flow yields a session (N26-style app approval, FinTS TAN) keep
    # it here so the user does not re-approve every sync. The user DB is encrypted at rest.
    # A static-secret connector never needs these.

    def load_session(self) -> str | None:
        with self.db.conn.read_ctx() as cursor:
            return self.db.get_dynamic_cache(
                cursor=cursor,
                name=DBCacheDynamic.BANK_SESSION,
                location=str(self.location),
                location_name=self.name,
            )

    def save_session(self, write_cursor: DBCursor, session: str) -> None:
        self.db.set_dynamic_cache(
            write_cursor=write_cursor,
            name=DBCacheDynamic.BANK_SESSION,
            value=session,
            location=str(self.location),
            location_name=self.name,
        )

    def clear_session(self, write_cursor: DBCursor) -> None:
        self.db.delete_dynamic_cache(
            write_cursor=write_cursor,
            name=DBCacheDynamic.BANK_SESSION,
            location=str(self.location),
            location_name=self.name,
        )

    # ---- cursor ----

    def get_cursor(self, cursor: DBCursor, account_id: str) -> Timestamp | None:
        return self.db.get_dynamic_cache(
            cursor=cursor,
            name=DBCacheDynamic.LAST_QUERY_TS,
            location=str(self.location),
            location_name=self.name,
            account_id=account_id,
        )

    def set_cursor(self, write_cursor: DBCursor, account_id: str, value: Timestamp) -> None:
        self.db.set_dynamic_cache(
            write_cursor=write_cursor,
            name=DBCacheDynamic.LAST_QUERY_TS,
            value=value,
            location=str(self.location),
            location_name=self.name,
            account_id=account_id,
        )

    def purge_local_state(self, write_cursor: DBCursor) -> None:
        """Drop cursors and session when the connection is removed"""
        self.db.delete_dynamic_caches(
            write_cursor=write_cursor,
            key_parts=[f'{self.location!s}_{self.name}_'],
        )

    # ---- exchange interface, generic for every bank ----

    def first_connection(self) -> None:
        self.first_connection_made = True

    def validate_api_key(self) -> tuple[bool, str]:
        try:
            self.query_accounts()
        except BankAuthExpired as e:
            return False, f'{self.manifest.display_name} rejected the credentials: {e!s}'
        except RemoteError as e:
            return False, f'Could not reach {self.manifest.display_name}: {e!s}'
        return True, ''

    @protect_with_lock()
    @cache_response_timewise()
    def query_balances(self, **kwargs: Any) -> ExchangeQueryBalances:
        try:
            accounts = self.query_accounts()
        except RemoteError as e:
            return None, f'Failed to query {self.manifest.display_name} balances. {e!s}'

        amounts: defaultdict[AssetWithOracles, FVal] = defaultdict(FVal)
        for account in accounts:
            if account.is_active and account.balance != ZERO:
                amounts[account.asset] += account.balance

        return dict(self.balances_from_amounts(amounts)), ''

    def _sync_account(
            self,
            account: BankAccount,
            updated_since: Timestamp | None,
    ) -> tuple[list[HistoryBaseEntry], Timestamp | None]:
        """Fetch one account's transactions and normalize them.

        Returns the events and the cursor value to persist once they are saved: the newest
        `updated_at` seen, or None when the bank gives none (then the sync stays full).
        """
        events: list[HistoryBaseEntry] = []
        newest: Timestamp | None = None
        for transaction in self.query_transactions(account=account, updated_since=updated_since):
            events.extend(bank_transaction_to_events(
                transaction=transaction,
                location=self.location,
                location_label=self.name,
            ))
            if transaction.updated_at is not None and (newest is None or transaction.updated_at > newest):  # noqa: E501
                newest = transaction.updated_at

        log.debug(
            'Synced %s %s %s events for account %s since %s',
            len(events), self.location, self.name, account.identifier, updated_since,
        )
        return events, newest

    def _updated_since(self, account_id: str, force_refresh: bool) -> Timestamp | None:
        if force_refresh:
            return None
        with self.db.conn.read_ctx() as cursor:
            saved = self.get_cursor(cursor=cursor, account_id=account_id)
        if saved is None:
            return None
        return Timestamp(max(0, saved - self.cursor_safety_window))

    def query_online_history_events(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
            force_refresh: bool = False,
    ) -> tuple[Sequence[HistoryBaseEntry], Timestamp]:
        """Cursor-based sync of every account. The exchange range arguments are ignored:
        the bank's own `updated_at` cursor decides what is fetched, and the framework's
        range bookkeeping only records that a sync up to `end_ts` happened."""
        events: list[HistoryBaseEntry] = []
        for account in self.query_accounts():
            account_events, _ = self._sync_account(
                account=account,
                updated_since=self._updated_since(account.identifier, force_refresh),
            )
            events.extend(account_events)
        return events, end_ts

    def _query_into_queue(
            self,
            end_ts: Timestamp,
            event_queue: HistoryEventQueue,
            force_refresh: bool,
    ) -> Timestamp:
        """Sync account by account, persisting each account's events together with its new
        cursor in one transaction, so a failure midway never advances a cursor past events
        that were not saved."""
        for account in self.query_accounts():
            events, newest = self._sync_account(
                account=account,
                updated_since=self._updated_since(account.identifier, force_refresh),
            )
            if newest is None:
                event_queue.flush(events=events)
                continue

            event_queue.flush(
                events=events,
                cursor_update=self._cursor_updater(account_id=account.identifier, value=newest),
            )
        return end_ts

    def _cursor_updater(self, account_id: str, value: Timestamp) -> Callable[[DBCursor], None]:
        def update(write_cursor: DBCursor) -> None:
            self.set_cursor(write_cursor=write_cursor, account_id=account_id, value=value)
        return update

    def query_online_history_events_into_queue(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
            event_queue: HistoryEventQueue,
    ) -> Timestamp:
        return self._query_into_queue(end_ts=end_ts, event_queue=event_queue, force_refresh=False)

    def requery_online_history_events_into_queue(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,
            event_queue: HistoryEventQueue,
    ) -> Timestamp:
        """A full resync: ignore the cursor. Converges to the same events by construction,
        since identity is the bank's transaction id."""
        return self._query_into_queue(end_ts=end_ts, event_queue=event_queue, force_refresh=True)

    def query_online_margin_history(
            self,
            start_ts: Timestamp,  # pylint: disable=unused-argument
            end_ts: Timestamp,  # pylint: disable=unused-argument
    ) -> list[MarginPosition]:
        return []


__all__ = ['BankConnector', 'BankError']
