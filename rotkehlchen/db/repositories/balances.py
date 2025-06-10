"""Repository for managing balance operations in the database."""
from typing import TYPE_CHECKING, Any, cast

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.structures.balance import Balance, BalanceType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.timing import HOUR_IN_SECONDS
from rotkehlchen.db.utils import (
    DBAssetBalance,
    LocationData,
    SingleDBAssetBalance,
)
from rotkehlchen.errors.asset import UnknownAsset
from rotkehlchen.errors.misc import InputError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.exchanges.data_structures import MarginPosition
from rotkehlchen.fval import FVal
from rotkehlchen.types import Location, Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.settings import ModifiableDBSettings
    from rotkehlchen.user_messages import MessagesAggregator


class BalancesRepository:
    """Repository for handling all balance-related operations."""

    def __init__(self, msg_aggregator: 'MessagesAggregator') -> None:
        """Initialize the balances repository."""
        self.msg_aggregator = msg_aggregator

    def add_multiple_balances(self, write_cursor: 'DBCursor', balances: list['DBAssetBalance']) -> None:  # noqa: E501
        """Execute addition of multiple balances in the DB"""
        serialized_balances = [balance.serialize_for_db() for balance in balances]
        try:
            write_cursor.executemany(
                'INSERT INTO timed_balances('
                '    category, timestamp, currency, amount, usd_value) '
                ' VALUES(?, ?, ?, ?, ?)',
                serialized_balances,
            )
        except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
            raise InputError('Adding timed_balance failed.') from e

    def add_multiple_location_data(
            self, write_cursor: 'DBCursor', location_data: list['LocationData'],
    ) -> None:
        """Execute addition of multiple location data in the DB"""
        # LocationData is a NamedTuple, so we can use it directly as a tuple
        serialized_data = [
            (entry.time, entry.location, entry.usd_value) for entry in location_data
        ]

        try:
            write_cursor.executemany(
                'INSERT INTO timed_location_data('
                '    timestamp, location, usd_value) '
                ' VALUES(?, ?, ?)',
                serialized_data,
            )
        except sqlcipher.DatabaseError as e:  # pylint: disable=no-member
            raise InputError(f'Tried to add a timed_location_data for {e!s}') from e

    def query_timed_balances(
            self,
            cursor: 'DBCursor',
            asset: Asset,
            balance_type: BalanceType,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
            settings: 'ModifiableDBSettings | None' = None,
    ) -> list['SingleDBAssetBalance']:
        """Query all balance entries for an asset and balance type within a range of timestamps"""
        if from_ts is None:
            from_ts = Timestamp(0)
        if to_ts is None:
            to_ts = ts_now()

        querystr = (
            'SELECT timestamp, amount, usd_value, category FROM timed_balances '
            'WHERE timestamp BETWEEN ? AND ? AND currency=?'
        )
        bindings = [from_ts, to_ts, asset.identifier]

        if settings is not None and settings.treat_eth2_as_eth and asset == A_ETH:
            querystr = querystr.replace('currency=?', 'currency IN (?,?)')
            bindings.append('ETH2')

        querystr += ' AND category=?'
        bindings.append(balance_type.serialize_for_db())
        querystr += ' ORDER BY timestamp ASC;'

        cursor.execute(querystr, bindings)
        results = cursor.fetchall()
        balances = []
        results_length = len(results)
        for idx, result in enumerate(results):
            entry_time = result[0]
            category = BalanceType.deserialize_from_db(result[3])
            balances.append(
                SingleDBAssetBalance(
                    time=entry_time,
                    amount=FVal(result[1]),
                    usd_value=FVal(result[2]),
                    category=category,
                ),
            )
            if settings is None or settings.ssf_graph_multiplier == 0 or idx == results_length - 1:
                continue

            next_result_time = results[idx + 1][0]
            balance_save_frequency = settings.balance_save_frequency if settings.balance_save_frequency is not None else 24  # noqa: E501
            ssf_graph_multiplier = settings.ssf_graph_multiplier if settings.ssf_graph_multiplier is not None else 0  # noqa: E501
            max_diff = balance_save_frequency * HOUR_IN_SECONDS * ssf_graph_multiplier
            while next_result_time - entry_time > max_diff:
                entry_time += max_diff
                balances.append(
                    SingleDBAssetBalance(
                        time=entry_time,
                        amount=FVal(result[1]),
                        usd_value=FVal(result[2]),
                        category=category,
                    ),
                )

        return balances

    def remove_queried_address_data(self, write_cursor: 'DBCursor', address: str, chain: str) -> None:  # noqa: E501
        """Remove the data for a queried address"""
        write_cursor.execute(
            'DELETE FROM blockchain_accounts WHERE blockchain=? AND account=?;',
            (chain, address),
        )

    def update_margin_positions(
            self,
            write_cursor: 'DBCursor',
            margin_positions: list['MarginPosition'],
    ) -> None:
        """Replaces all margin positions saved in the DB with those given here"""
        write_cursor.execute('DELETE FROM margin_positions;')
        write_cursor.executemany(
            'INSERT INTO margin_positions(id, location, open_time, '
            'close_time, profit_loss, pl_currency, fee, fee_currency, link, notes) '
            'VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
            [mp.serialize_for_db() for mp in margin_positions],
        )

    def get_margin_positions(
            self,
            cursor: 'DBCursor',
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
            location: Location | None = None,
    ) -> list['MarginPosition']:
        """Returns all margin positions from the DB for the given time period and location

        Optionally filter by location
        """
        querystr = 'SELECT id, location, open_time, close_time, profit_loss, pl_currency, fee, fee_currency, link, notes FROM margin_positions '  # noqa: E501
        filters = []
        if location is not None:
            filters.append(f'location="{location.serialize_for_db()}" ')
        if from_ts is not None:
            filters.append(f'close_time >= {from_ts} ')
        if to_ts is not None:
            filters.append(f'close_time <= {to_ts} ')
        if filters:
            querystr += 'WHERE ' + 'AND '.join(filters)
        querystr += 'ORDER BY close_time ASC;'

        cursor.execute(querystr)
        margin_positions = []
        for result in cursor:
            try:
                margin_position = MarginPosition.deserialize_from_db(result)
            except DeserializationError as e:
                self.msg_aggregator.add_error(
                    f'Error deserializing margin position from the DB. '
                    f'Skipping it. Error was: {e!s}',
                )
                continue
            except UnknownAsset as e:
                self.msg_aggregator.add_error(
                    f'Unknown asset {e.identifier} found in margin position. '
                    f'Ignoring the margin position.',
                )
                continue
            margin_positions.append(margin_position)

        return margin_positions

    def save_balances_data(
            self, write_cursor: 'DBCursor', data: dict[str, Any], timestamp: Timestamp,
    ) -> None:
        """The keys of the data dictionary can be any kind of asset plus 'location'
        and 'net_usd'. This gives us the balance data per assets, the balance data
        per location and finally the total balance

        The balances are saved in the DB at the given timestamp
        """
        balances = []
        locations = []

        for key, val in data['assets'].items():
            msg = f'at this point the key should be of Asset type and not {type(key)} {key!s}'
            assert isinstance(key, Asset), msg
            balances.append(DBAssetBalance(
                category=BalanceType.ASSET,
                time=timestamp,
                asset=key,
                amount=val['amount'],
                usd_value=val['usd_value'],
            ))

        for key, val in data['liabilities'].items():
            msg = f'at this point the key should be of Asset type and not {type(key)} {key!s}'
            assert isinstance(key, Asset), msg
            balances.append(DBAssetBalance(
                category=BalanceType.LIABILITY,
                time=timestamp,
                asset=key,
                amount=val['amount'],
                usd_value=val['usd_value'],
            ))

        for key2, val2 in data['location'].items():
            # Here we know val2 is just a Dict since the key to data is 'location'
            val2 = cast('dict', val2)
            location = Location.deserialize(key2).serialize_for_db()
            locations.append(LocationData(
                time=timestamp, location=location, usd_value=str(val2['usd_value']),
            ))
        locations.append(LocationData(
            time=timestamp,
            location=Location.TOTAL.serialize_for_db(),  # pylint: disable=no-member
            usd_value=str(data['net_usd']),
        ))
        try:
            self.add_multiple_balances(write_cursor, balances)
            self.add_multiple_location_data(write_cursor, locations)
        except InputError as err:
            self.msg_aggregator.add_warning(str(err))

    def get_historical_balance(
            self,
            cursor: 'DBCursor',
            asset: Asset,
            timestamp: Timestamp,
            balance_type: BalanceType | None = None,
    ) -> Balance:
        """Get the historical balance of an asset at a specific timestamp

        If no balance is found a 0 balance is returned
        """
        querystr = 'SELECT amount, usd_value FROM timed_balances WHERE currency=? AND timestamp=?'
        bindings = [asset.identifier, timestamp]
        if balance_type is not None:
            querystr += ' AND category=?'
            bindings.append(balance_type.serialize_for_db())

        cursor.execute(querystr, bindings)
        result = cursor.fetchone()
        if result is None:
            return Balance()

        return Balance(amount=FVal(result[0]), usd_value=FVal(result[1]))

    def get_associated_locations(self, cursor: 'DBCursor') -> set[Location]:
        """Get all locations that have associated data in the database."""
        cursor.execute(
            'SELECT location FROM margin_positions UNION '
            'SELECT location FROM user_credentials UNION '
            'SELECT location FROM history_events',
        )
        return {Location.deserialize_from_db(loc[0]) for loc in cursor}

    def get_last_balance_save_time(self, cursor: 'DBCursor') -> Timestamp:
        """Get the timestamp of the last balance save."""
        cursor.execute(
            'SELECT MAX(timestamp) FROM timed_location_data',
        )
        result = cursor.fetchone()
        if result is None or result[0] is None:
            return Timestamp(0)
        return Timestamp(result[0])

    def should_save_balances(
            self,
            cursor: 'DBCursor',
            balance_save_frequency: int,
            last_query_ts: Timestamp | None = None,
    ) -> bool:
        """
        Returns whether we should save a balance snapshot depending on whether the last snapshot
        and last query timestamps are older than the period defined by the save frequency setting.
        """
        # Setting is saved in hours, convert to seconds here
        period = balance_save_frequency * 60 * 60
        now = ts_now()
        if last_query_ts is not None and now - last_query_ts < period:
            return False

        last_save = self.get_last_balance_save_time(cursor)
        return now - last_save > period

    @staticmethod
    def _infer_zero_timed_balances(
            cursor: 'DBCursor',
            balances: list[SingleDBAssetBalance],
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
    ) -> list[SingleDBAssetBalance]:
        """
        Given a list of asset specific timed balances, infers the missing zero timed balances
        for the asset. We add 0 balances on the start and end of a period of 0 balances.
        It addresses this issue: https://github.com/rotki/rotki/issues/2822

        Example
        We have the following timed balances for ETH (value, time):
        (1, 1), (1, 2), (2, 3), (5, 7), (5, 12)
        The timestamps of all timed balances in the DB are:
        (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12)
        So we need to infer the following zero timed balances:
        (0, 4), (0, 6), (0, 8), (0, 11)

        Keep in mind that in a case like this (1, 1), (1, 2), (5, 4) we will infer (0, 3)
        despite the fact that it is not strictly needed by the front end.
        """
        from rotkehlchen.constants import ZERO

        if len(balances) == 0:
            return []

        if from_ts is None:
            from_ts = Timestamp(0)
        if to_ts is None:
            to_ts = ts_now()

        cursor.execute(
            'SELECT COUNT(DISTINCT timestamp) FROM timed_balances WHERE timestamp BETWEEN ? AND ?',
            (from_ts, to_ts),
        )
        num_distinct_timestamps = cursor.fetchone()[0]

        asset_timestamps = [b.time for b in balances if b.amount != ZERO]  # ignore timestamps from 0 balances added by the ssf_graph_multiplier setting  # noqa: E501
        if len(asset_timestamps) == num_distinct_timestamps:
            return []

        cursor.execute(
            'SELECT timestamp, category FROM timed_balances WHERE timestamp BETWEEN ? AND ? '
            'ORDER BY timestamp ASC',
            (from_ts, to_ts),
        )
        results = cursor.fetchall()
        if not results:
            return []

        all_timestamps, _all_categories = zip(*results, strict=True)

        # Create a mapping of timestamp to category for the asset balances
        asset_timestamp_to_category = {b.time: b.category for b in balances if b.amount != ZERO}

        # dicts maintain insertion order in python 3.7+
        timestamps_have_asset_balance = dict.fromkeys(all_timestamps, False)
        timestamps_with_asset_balance = dict.fromkeys(asset_timestamps, True)
        timestamps_have_asset_balance.update(timestamps_with_asset_balance)
        prev_has_asset_balance = timestamps_have_asset_balance[all_timestamps[0]]  # the value of the first timestamp  # noqa: E501
        prev_timestamp = all_timestamps[0]
        inferred_balances: list[SingleDBAssetBalance] = []
        is_zero_period_open = False
        # For the last category, use the category from the last balance with amount > 0
        last_asset_category = BalanceType.ASSET  # default
        for balance in reversed(balances):
            if balance.amount > ZERO:
                last_asset_category = balance.category
                break

        for idx, (timestamp, has_asset_balance) in enumerate(timestamps_have_asset_balance.items()):  # noqa: E501
            if idx == len(timestamps_have_asset_balance) - 1 and has_asset_balance is False:
                # If there is no balance for the last timestamp add a zero balance.
                inferred_balances.append(
                    SingleDBAssetBalance(
                        time=timestamp,
                        amount=ZERO,
                        usd_value=ZERO,
                        category=last_asset_category,
                    ),
                )
            elif has_asset_balance is False and prev_has_asset_balance is True:
                # add the start of a zero balance period
                # Find the category of the previous asset balance
                category_to_use = last_asset_category
                if prev_timestamp in asset_timestamp_to_category:
                    category_to_use = asset_timestamp_to_category[prev_timestamp]

                inferred_balances.append(
                    SingleDBAssetBalance(
                        time=timestamp,
                        amount=ZERO,
                        usd_value=ZERO,
                        category=category_to_use,
                    ),
                )
                is_zero_period_open = True
            elif has_asset_balance is True and prev_has_asset_balance is False and is_zero_period_open is True:  # noqa: E501
                # add the end of a zero balance period
                inferred_balances.append(
                    SingleDBAssetBalance(
                        time=prev_timestamp,
                        amount=ZERO,
                        usd_value=ZERO,
                        category=inferred_balances[-1].category,  # the category of the asset at the start of the zero balance period  # noqa: E501
                    ),
                )
                is_zero_period_open = False
                if timestamp in asset_timestamp_to_category:
                    last_asset_category = asset_timestamp_to_category[timestamp]
            elif has_asset_balance is True and timestamp in asset_timestamp_to_category:
                last_asset_category = asset_timestamp_to_category[timestamp]
            prev_has_asset_balance, prev_timestamp = has_asset_balance, timestamp
        return inferred_balances

    def query_collection_timed_balances(
            self,
            cursor: 'DBCursor',
            collection_id: int,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
    ) -> list[SingleDBAssetBalance]:
        """Query all balance entries for all assets of a collection within a range of timestamps
        """
        from rotkehlchen.db.utils import combine_asset_balances
        from rotkehlchen.globaldb.handler import GlobalDBHandler

        with GlobalDBHandler().conn.read_ctx() as global_cursor:
            global_cursor.execute(
                'SELECT asset FROM multiasset_mappings WHERE collection_id=?',
                (collection_id,),
            )
            asset_balances: list[SingleDBAssetBalance] = []
            for x in global_cursor:
                asset_balances.extend(self.query_timed_balances(
                    cursor=cursor,
                    asset=Asset(x[0]),
                    balance_type=BalanceType.ASSET,
                    from_ts=from_ts,
                    to_ts=to_ts,
                ))

        asset_balances.sort(key=lambda x: x.time)
        return combine_asset_balances(asset_balances)
