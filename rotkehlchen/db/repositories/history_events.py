"""Repository for managing history events and related data in the database."""
import logging
from typing import TYPE_CHECKING, Any

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_ETH, A_ETH2
from rotkehlchen.db.utils import LocationData, DBAssetBalance
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.user_messages import MessagesAggregator

log = logging.getLogger(__name__)


class HistoryEventsRepository:
    """Repository for handling all history events operations."""

    def __init__(self, msg_aggregator: 'MessagesAggregator') -> None:
        """Initialize the history events repository."""
        self.msg_aggregator = msg_aggregator

    def add_margin_positions(
            self,
            write_cursor: 'DBCursor',
            margin_positions: list[MarginPosition],
    ) -> None:
        """Add margin positions to the database."""
        margin_tuples: list[tuple[Any, ...]] = []
        for margin in margin_positions:
            open_time = 0 if margin.open_time is None else margin.open_time
            margin_tuples.append((
                margin.identifier,
                margin.location.serialize_for_db(),
                open_time,
                margin.close_time,
                str(margin.profit_loss),
                margin.pl_currency.identifier,
                str(margin.fee),
                margin.fee_currency.identifier,
                margin.link,
                margin.notes,
            ))

        query = """
            INSERT OR IGNORE INTO margin_positions(
              id,
              location,
              open_time,
              close_time,
              profit_loss,
              pl_currency,
              fee,
              fee_currency,
              link,
              notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        # Execute one by one to be able to log duplicates
        for margin_tuple in margin_tuples:
            write_cursor.execute(query, margin_tuple)
            if write_cursor.rowcount == 0:
                log.warning(
                    f'Did not add "Margin position with id {margin_tuple[0]}" to the '
                    f'database as it already exists',
                )

    def get_latest_location_value_distribution(
            self,
            cursor: 'DBCursor',
    ) -> list[LocationData]:
        """Gets the latest location data

        Returns a list of `LocationData` all at the latest timestamp.
        Essentially this returns the distribution of netvalue across all locations
        """
        cursor.execute(
            'SELECT timestamp, location, usd_value FROM timed_location_data WHERE '
            'timestamp=(SELECT MAX(timestamp) FROM timed_location_data) AND usd_value!=0;',
        )
        return [LocationData(
            time=x[0],
            location=x[1],
            usd_value=x[2],
        ) for x in cursor]

    def get_latest_asset_value_distribution(
            self,
            cursor: 'DBCursor',
            ignored_asset_ids: set[str],
            treat_eth2_as_eth: bool,
    ) -> list[DBAssetBalance]:
        """Gets the latest asset distribution data

        Returns a list of `DBAssetBalance` all at the latest timestamp.
        Essentially this returns the distribution of netvalue across all assets

        This will NOT include liabilities

        The list is sorted by usd value going from higher to lower
        """
        cursor.execute(
            'SELECT timestamp, currency, amount, usd_value, category FROM timed_balances '
            'WHERE timestamp=(SELECT MAX(timestamp) from timed_balances) AND category = ? '
            'ORDER BY CAST(usd_value AS REAL) DESC;',
            (BalanceType.ASSET.serialize_for_db(),),  # pylint: disable=no-member
        )
        asset_balances = []
        eth_balance = DBAssetBalance(
            time=Timestamp(0),
            category=BalanceType.ASSET,
            asset=A_ETH,
            amount=ZERO,
            usd_value=ZERO,
        )
        
        from rotkehlchen.assets.asset import Asset
        for result in cursor:
            asset = Asset(result[1]).check_existence()
            time = Timestamp(result[0])
            amount = FVal(result[2])
            usd_value = FVal(result[3])
            if asset.identifier in ignored_asset_ids:
                continue
            # show eth & eth2 as eth in value distribution by asset
            if treat_eth2_as_eth is True and asset in (A_ETH, A_ETH2):
                eth_balance.time = time
                eth_balance.amount += amount
                eth_balance.usd_value += usd_value
                continue

            else:
                asset_balances.append(
                    DBAssetBalance(
                        time=time,
                        asset=asset,
                        amount=amount,
                        usd_value=usd_value,
                        category=BalanceType.deserialize_from_db(result[4]),
                    ),
                )
        # only add the eth_balance if it contains a balance > 0
        if eth_balance.amount > ZERO:
            # respect descending order `usd_value`
            for index, balance in enumerate(asset_balances):
                if eth_balance.usd_value > balance.usd_value:
                    asset_balances.insert(index, eth_balance)
                    break
            else:
                asset_balances.append(eth_balance)

        return asset_balances

    def get_netvalue_data(
            self,
            cursor: 'DBCursor',
            from_ts: Timestamp,
            include_nfts: bool = True,
    ) -> tuple[list[str], list[str]]:
        """Get all entries of net value data from the DB"""
        cursor.execute(  # Get the total location ("H") entries in ascending time
            "SELECT timestamp, usd_value FROM timed_location_data "
            "WHERE location='H' AND timestamp >= ? ORDER BY timestamp ASC;",
            (from_ts,),
        )
        if not include_nfts:
            nft_cursor = cursor  # use same cursor
            nft_cursor.execute(
                'SELECT timestamp, SUM(usd_value) FROM timed_balances WHERE '
                'timestamp >= ? AND currency LIKE ? GROUP BY timestamp',
                (from_ts, f'{NFT_DIRECTIVE}%'),
            )
            nft_values = dict(nft_cursor)

        data, times_int = [], []
        for entry in cursor:
            times_int.append(entry[0])
            if include_nfts:
                total = entry[1]
            else:
                total = str(FVal(entry[1]) - FVal(nft_values.get(entry[0], 0)))  # pyright: ignore  # nft_values is populated when include_nfts is False

            data.append(total)

        return times_int, data