from rotkehlchen.greenlets import GreenletManager
from rotkehlchen.db.dbhandler import DBHandler
from typing import NamedTuple
from rotkehlchen.assets.asset import Asset
from rotkehlchen.externalapis.cryptocompare import Cryptocompare
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.typing import Timestamp
from rotkehlchen.premium.sync import PremiumSyncManager
from rotkehlchen.chain.manager import ChainManager
from rotkehlchen.chain.bitcoin.xpub import XpubManager

CRYPTOCOMPARE_QUERY_AFTER_SECS = 86400  # a day
MAX_TASKS_NUM = 2


class CCHistoQuery(NamedTuple):
    from_asset: Asset
    to_asset: Asset


class TaskManager():

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: DBHandler,
            cryptocompare: Cryptocompare,
            premium_sync_manager: PremiumSyncManager,
            chain_manager: ChainManager,
    ) -> None:
        self.greenlet_manager = greenlet_manager
        self.database = database
        self.premium_sync_manager = premium_sync_manager
        self.cryptocompare_queries = set()
        self.chain_manager = chain_manager
        self.xpub_derivation_scheduled = False

    def _prepare_cryptocompare_queries(self, now_ts: Timestamp) -> None:
        if len(self.cryptocompare_queries) != 0:
            return
        assets = self.database.query_owned_assets()
        main_currency = self.database.get_main_currency()
        for asset in assets:
            data = self.cryptocompare.get_cached_data(from_asset=asset, to_asset=main_currency)
            if data is not None and now_ts - data.end_time < CRYPTOCOMPARE_QUERY_AFTER_SECS:
                continue

            self.cryptocompare_queries.add(CCHistoQuery(from_asset=asset, to_asset=main_currency))

    def _maybe_schedule_cryptocompare_query(self) -> bool:
        """Schedules a cryptocompare query for a single asset history"""
        now_ts = ts_now()
        self._prepare_cryptocompare_queries(now_ts)
        if len(self.cryptocompare_queries) == 0:
            return False

        query = self.cryptocompare_queries.pop()
        task_name = f'Cryptocompare historical prices {query.from_asset} / {query.to_asset} query'
        self.greenlet_manager.spawn_and_track(
            after_seconds=None,
            task_name=task_name,
            method=self.cryptocompare.get_historical_data,
            from_asset=query.from_asset,
            to_asset=query.to_asset,
            timestamp=now_ts,
            only_check_cache=False,
        )
        return True

    def schedule(self) -> None:
        """Schedules background tasks"""
        if len(self.greenlet_manager.greenlets) > MAX_TASKS_NUM:
            return  # too busy

        self._maybe_schedule_cryptocompare_query()
        self.premium_sync_manager.maybe_upload_data_to_server()

        if not self.xpub_derivation_scheduled:
            # 1 minute in the app's startup try to derive new xpub addresses
            self.greenlet_manager.spawn_and_track(
                after_seconds=60.0,
                task_name='Derive new xpub addresses',
                method=XpubManager(self.chain_manager).check_for_new_xpub_addresses,
            )
            self.xpub_derivation_scheduled = True
