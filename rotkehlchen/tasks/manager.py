import logging
from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.db.dbhandler import DBHandler
from typing import NamedTuple, Set
from rotkehlchen.assets.asset import Asset
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.premium.sync import PremiumSyncManager
from rotkehlchen.chain.manager import ChainManager
from rotkehlchen.chain.bitcoin.xpub import XpubManager

logger = logging.getLogger(__name__)


CRYPTOCOMPARE_QUERY_AFTER_SECS = 86400  # a day
DEFAULT_MAX_TASKS_NUM = 2
CRYPTOCOMPARE_HISTOHOUR_FREQUENCY = 240  # at least 4 mins apart


class CCHistoQuery(NamedTuple):
    from_asset: Asset
    to_asset: Asset


class TaskManager():

    def __init__(
            self,
            max_tasks_num: int,
            greenlet_manager: GreenletManager,
            database: DBHandler,
            cryptocompare: Cryptocompare,
            premium_sync_manager: PremiumSyncManager,
            chain_manager: ChainManager,
    ) -> None:
        self.max_tasks_num = max_tasks_num
        self.greenlet_manager = greenlet_manager
        self.database = database
        self.cryptocompare = cryptocompare
        self.premium_sync_manager = premium_sync_manager
        self.cryptocompare_queries: Set[CCHistoQuery] = set()
        self.chain_manager = chain_manager
        self.xpub_derivation_scheduled = False
        self.prepared_cryptocompare_query = False
        self.greenlet_manager.spawn_and_track(  # Needs to run in greenlet, is slow
            after_seconds=None,
            task_name='Prepare cryptocompare queries',
            exception_is_error=True,
            method=self._prepare_cryptocompare_queries,
        )

    def _prepare_cryptocompare_queries(self) -> None:
        """Prepare the queries to do to cryptocompare

        This would be really slow if the entire json cache files were read but we
        have implemented get_cached_data_metadata to only read the relevant part of the file.
        Before doing that we had to yield with gevent.sleep() at each loop iteration.

        Runs only once in the beginning and then has a number of queries prepared
        for the task manager to schedule
        """
        now_ts = ts_now()
        if self.prepared_cryptocompare_query is True:
            return

        if len(self.cryptocompare_queries) != 0:
            return

        self.preparing_cryptocompare_query = True
        assets = self.database.query_owned_assets()
        main_currency = self.database.get_main_currency()
        for asset in assets:

            if asset.is_fiat() and main_currency.is_fiat():
                continue  # ignore fiat to fiat

            if asset.cryptocompare == '' or main_currency.cryptocompare == '':
                continue  # not supported in cryptocompare

            data = self.cryptocompare.get_cached_data_metadata(
                from_asset=asset,
                to_asset=main_currency,
            )
            if data is not None and now_ts - data[1] < CRYPTOCOMPARE_QUERY_AFTER_SECS:
                continue

            self.cryptocompare_queries.add(CCHistoQuery(from_asset=asset, to_asset=main_currency))

        self.prepared_cryptocompare_query = True

    def _maybe_schedule_cryptocompare_query(self) -> bool:
        """Schedules a cryptocompare query for a single asset history"""
        if self.prepared_cryptocompare_query is False:
            return False

        if len(self.cryptocompare_queries) == 0:
            return False

        # If there is already a cryptocompary query running don't schedule another
        if any(
                'Cryptocompare historical prices' in x.task_name
                for x in self.greenlet_manager.greenlets
        ):
            return False

        now_ts = ts_now()
        # Make sure there is a long enough period  between an asset's histohour query
        # to avoid getting rate limited by cryptocompare
        if now_ts - self.cryptocompare.last_histohour_query_ts <= CRYPTOCOMPARE_HISTOHOUR_FREQUENCY:  # noqa: E501
            return False

        query = self.cryptocompare_queries.pop()
        task_name = f'Cryptocompare historical prices {query.from_asset} / {query.to_asset} query'
        logger.debug(f'Scheduling task for {task_name}')
        self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            exception_is_error=False,
            method=self.cryptocompare.get_historical_data,
            from_asset=query.from_asset,
            to_asset=query.to_asset,
            timestamp=now_ts,
            only_check_cache=False,
        )
        return True

    def schedule(self) -> None:
        """Schedules background tasks"""
        self.greenlet_manager.clear_finished()
        current_greenlets = len(self.greenlet_manager.greenlets)
        not_proceed = current_greenlets >= self.max_tasks_num
        logger.debug(
            f'At task scheduling. Current greenlets: {current_greenlets} '
            f'Max greenlets: {self.max_tasks_num}. '
            f'{"Will not schedule" if not_proceed else "Will schedule"}.',
        )
        if not_proceed:
            return  # too busy

        self._maybe_schedule_cryptocompare_query()
        self.premium_sync_manager.maybe_upload_data_to_server()

        if not self.xpub_derivation_scheduled:
            # 1 minute in the app's startup try to derive new xpub addresses
            self.greenlet_manager.spawn_and_track(
                after_seconds=60.0,
                task_name='Derive new xpub addresses',
                exception_is_error=True,
                method=XpubManager(self.chain_manager).check_for_new_xpub_addresses,
            )
            self.xpub_derivation_scheduled = True
