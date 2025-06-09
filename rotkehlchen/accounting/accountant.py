import logging
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from more_itertools import peekable

from rotkehlchen.accounting.constants import FREE_PNL_EVENTS_LIMIT
from rotkehlchen.accounting.export.csv import CSVExporter
from rotkehlchen.accounting.pot import AccountingPot
from rotkehlchen.accounting.types import EventAccountingRuleStatus, MissingPrice
from rotkehlchen.chain.evm.accounting.aggregator import EVMAccountingAggregators
from rotkehlchen.db.reports import DBAccountingReports
from rotkehlchen.db.settings import DBSettings
from rotkehlchen.errors.asset import UnknownAsset, UnprocessableTradePair, UnsupportedAsset
from rotkehlchen.errors.misc import AccountingError, RemoteError
from rotkehlchen.errors.price import NoPriceForGivenTimestamp, PriceQueryUnsupportedAsset
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import EVM_CHAIN_IDS_WITH_TRANSACTIONS, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.data_structures import DefaultLRUCache, LRUCacheWithRemove
from rotkehlchen.utils.concurrency import sleep

if TYPE_CHECKING:
    from rotkehlchen.accounting.mixins.event import AccountingEventMixin
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# size assumes a user loads 5 pages of 100 events each one
# and each event having in average 3 subevents.
# TODO: Make this changeable depending on user's set page size
PROCESSABLE_EVENTS_CACHE_SIZE = 1500


class Accountant:

    def __init__(
            self,
            db: 'DBHandler',
            msg_aggregator: MessagesAggregator,
            chains_aggregator: 'ChainsAggregator',
            premium: Premium | None,
    ) -> None:
        self.db = db
        self.msg_aggregator = msg_aggregator
        self.csvexporter = CSVExporter(database=db)
        evm_accounting_aggregators = EVMAccountingAggregators([chains_aggregator.get_evm_manager(x).accounting_aggregator for x in EVM_CHAIN_IDS_WITH_TRANSACTIONS])  # noqa: E501

        # TODO: Allow for setting of multiple accounting pots
        self.pots = [
            AccountingPot(
                database=db,
                evm_accounting_aggregators=evm_accounting_aggregators,
                msg_aggregator=msg_aggregator,
                is_dummy_pot=False,
            ),
        ]

        self.currently_processing_timestamp = Timestamp(-1)
        self.first_processed_timestamp = Timestamp(-1)
        self.premium = premium
        # cache to know what events will be processed or not during accounting
        self.processable_events_cache: LRUCacheWithRemove[int, EventAccountingRuleStatus] = LRUCacheWithRemove(maxsize=PROCESSABLE_EVENTS_CACHE_SIZE)  # noqa: E501
        # map event rules signatures to a list of event identifiers affected by them
        # used to know which events need to be invalidated when updating a rule
        self.processable_events_cache_signatures: DefaultLRUCache[int, list[int]] = DefaultLRUCache(default_factory=list, maxsize=PROCESSABLE_EVENTS_CACHE_SIZE)  # noqa: E501
        self.ignored_asset_ids: set[str] = set()  # populated in process_history so that we load them in memory once during accounting and not reload them from the DB for every single event processing  # noqa: E501

    def activate_premium_status(self, premium: Premium) -> None:
        self.premium = premium

    def deactivate_premium_status(self) -> None:
        self.premium = None

    @property
    def query_start_ts(self) -> Timestamp:
        return self.pots[0].query_start_ts

    @property
    def query_end_ts(self) -> Timestamp:
        return self.pots[0].query_end_ts

    def _process_skipping_exception(
            self,
            exception: Exception,
            events: Sequence['AccountingEventMixin'],
            count: int,
            reason: str,
    ) -> int:
        event = events[count]
        ts = event.get_timestamp()
        identifier = event.get_identifier()
        self.msg_aggregator.add_error(
            f'Skipping event with id {identifier} at '
            f'{self.csvexporter.timestamp_to_date(ts)} '
            f'during history processing due to {reason}: '
            f'{exception!s}. Check the logs for more details',
        )
        log.error(
            f'Skipping event with id {identifier}  during history processing due to '
            f'{reason}: {exception!s}',
        )
        return count + 1

    def process_history(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            events: Sequence['AccountingEventMixin'],
    ) -> int:
        """Processes the entire history of cryptoworld actions in order to determine
        the price and time at which every asset was obtained and also
        the general and taxable profit/loss.

        The events history is already expected to be sorted when passed to this function.

        start_ts here is the timestamp at which to start taking trades and other
        taxable events into account. Not where processing starts from. Processing
        always starts from the very first event we find in the history.

        Returns the id of the generated report
        """
        active_premium = self.premium and self.premium.is_active()
        log.info(
            'Start of history processing',
            start_ts=start_ts,
            end_ts=end_ts,
            active_premium=active_premium,
        )
        events_limit = -1 if active_premium else FREE_PNL_EVENTS_LIMIT
        # Ask the DB for the settings once at the start of processing so we got the
        # same settings through the entire task
        with self.db.conn.read_ctx() as cursor:
            db_settings = self.db.get_settings(cursor)
            self.ignored_asset_ids = self.db.get_ignored_asset_ids(cursor)
            # Create a new pnl report in the DB to be used to save each generated event
            dbpnl = DBAccountingReports(self.db)
            first_ts = Timestamp(0) if len(events) == 0 else events[0].get_timestamp()
            report_id = dbpnl.add_report(
                first_processed_timestamp=first_ts,
                start_ts=start_ts,
                end_ts=end_ts,
                settings=db_settings,
            )
            self.pots[0].reset(settings=db_settings, start_ts=start_ts, end_ts=end_ts, report_id=report_id)  # noqa: E501
            self.end_ts = end_ts
            self.csvexporter.reset(start_ts=start_ts, end_ts=end_ts)

            # The first ts is the ts of the first action we have in history or 0 for empty history
            self.currently_processing_timestamp = first_ts
            self.first_processed_timestamp = first_ts

            count = 0
            actions_length = len(events)
            prev_time = last_event_ts = Timestamp(0)
            ignored_ids = self.db.get_ignored_action_ids(cursor=cursor)

        events_iter = peekable(events)
        while True:
            try:
                (
                    processed_events_num,
                    prev_time,
                ) = self._process_event(
                    events_iterator=events_iter,
                    start_ts=start_ts,
                    end_ts=end_ts,
                    prev_time=prev_time,
                    db_settings=db_settings,
                    ignored_ids=ignored_ids,
                )
            except PriceQueryUnsupportedAsset as e:
                count = self._process_skipping_exception(
                    exception=e,
                    events=events,
                    count=count,
                    reason='not being able to find price for an unsupported asset',
                )
                continue
            except NoPriceForGivenTimestamp as e:
                self.pots[0].cost_basis.missing_prices.add(
                    MissingPrice(
                        from_asset=e.from_asset,
                        to_asset=e.to_asset,
                        time=e.time,
                        rate_limited=e.rate_limited,
                    ),
                )
                continue
            except RemoteError as e:
                count = self._process_skipping_exception(
                    exception=e,
                    events=events,
                    count=count,
                    reason='inability to reach an external service at that point in time',
                )
                continue
            except AccountingError as e:
                log.error(f'Found critical error {e} when processing history. Stopping.')
                e.report_id = report_id
                raise

            if processed_events_num == 0:
                break  # we reached the period end

            last_event_ts = prev_time
            if count % 500 == 0:
                # This loop can take a very long time depending on the amount of events
                # to process. We need to yield to other tasks or else calls to the
                # API may time out
                sleep(0.5)
            count += processed_events_num
            if not active_premium and count >= FREE_PNL_EVENTS_LIMIT:
                log.debug(
                    f'PnL reports event processing has hit the event limit of {events_limit}. '
                    f'Processing stopped and the results will not '
                    f'take into account subsequent events. Total events were {len(events)}',
                )
                break

        dbpnl.add_report_overview(
            report_id=report_id,
            last_processed_timestamp=last_event_ts,
            processed_actions=count,
            total_actions=actions_length,
            pnls=self.pots[0].pnls,
        )

        for pot in self.pots:  # delete rules stored in memory since they won't be needed and can be queried again from the db  # noqa: E501
            pot.events_accountant.rules_manager.clean_rules()

        self.ignored_asset_ids.clear()  # clean ignored assets from memory once PnL report run concludes  # noqa: E501
        return report_id

    def _process_event(
            self,
            events_iterator: "peekable['AccountingEventMixin']",
            start_ts: Timestamp,
            end_ts: Timestamp,
            prev_time: Timestamp,
            db_settings: DBSettings,
            ignored_ids: set[str],
    ) -> tuple[int, Timestamp]:
        """Processes each individual event and returns a tuple with processing information:
        - How many events were consumed (0 to indicate we finished processing)
        - last event timestamp

        May raise:
        - PriceQueryUnsupportedAsset if from/to asset is missing from price oracles
        - NoPriceForGivenTimestamp if we can't find a price for the asset in the given
        timestamp from the price oracle
        - RemoteError if there is a problem reaching the price oracle server
        or with reading the response returned by the server
        """
        event = next(events_iterator, None)
        if event is None:
            return 0, prev_time

        # Assert we are sorted in ascending time order.
        timestamp = event.get_timestamp()
        prev_time = timestamp
        if not db_settings.calculate_past_cost_basis and timestamp < start_ts:
            # ignore older events than start_ts if we don't want past cost basis
            return 1, prev_time

        if timestamp > end_ts:
            # reached the end of the time period for the report
            return 0, prev_time

        self.currently_processing_timestamp = timestamp
        try:
            event_assets = event.get_assets()
        except UnknownAsset as e:
            self.msg_aggregator.add_warning(
                f'At history processing found event with unknown asset {e.identifier}. '
                f'Ignoring the event.',
            )
            return 1, prev_time
        except UnsupportedAsset as e:
            self.msg_aggregator.add_warning(
                f'At history processing found event with unsupported asset {e.identifier}. '
                f'Ignoring the event.',
            )
            return 1, prev_time
        except UnprocessableTradePair as e:
            self.msg_aggregator.add_error(
                f'At history processing found event with unprocessable trade pair {e!s} '
                f'Ignoring the event.',
            )
            return 1, prev_time

        if any(x.identifier in self.ignored_asset_ids for x in event_assets):
            log.debug(
                'Ignoring event with ignored asset',
                event_type=event.get_accounting_event_type(),
                assets=[x.identifier for x in event_assets],
            )
            return 1, prev_time

        if event.should_ignore(ignored_ids):
            log.info(
                f'Ignoring event with identifier {event.get_identifier()} '
                f'at {timestamp} since the user asked to ignore it',
            )
            return 1, prev_time

        consumed_events = event.process(self.pots[0], events_iterator)
        return consumed_events, prev_time

    def export(self, directory_path: Path | None) -> tuple[bool, str]:
        """Export the PnL report. Only CSV for now

        If a directory is given, it simply exports all event.csv in the given directory.
        If no directory is given it returns the path to a zip to export
        """
        if len(self.pots[0].processed_events) == 0:
            return False, 'No history processed in order to perform an export'

        if directory_path is None:
            return self.csvexporter.create_zip(
                events=self.pots[0].processed_events,
                pnls=self.pots[0].pnls,
            )

        return self.csvexporter.export(
            events=self.pots[0].processed_events,
            pnls=self.pots[0].pnls,
            directory=directory_path,
        )
