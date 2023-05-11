import logging
from typing import TYPE_CHECKING, Literal, Union

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.structures.base import HistoryBaseEntryType
from rotkehlchen.chain.ethereum.modules.eth2.structures import Eth2Validator, ValidatorDailyStats
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.filtering import ETH_STAKING_EVENT_JOIN, EthStakingEventFilterQuery
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp, TimestampMS

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.filtering import Eth2DailyStatsFilterQuery

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# How much time more than the last time a withdrawal happened to have allowed to pass
# in order to recheck withdrawals for a given validator. In average at time of writing
# withdrawals occur every 3-5 days for a single validator
WITHDRAWALS_RECHECK_PERIOD = 3 * DAY_IN_SECONDS * 1000  # 3 days in milliseconds


class DBEth2():

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def get_validators_to_query_for_withdrawals(self, up_to_tsms: TimestampMS) -> list[tuple[int, TimestampMS]]:  # noqa: E501
        """Gets a list of validators that need to be queried for new withdrawals

        Validators need to be queried if last time they are queried was more than X seconds.

        Returns a list of tuples. First entry is validator index and second entry is
        last queried timestamp in milliseconds for daily stats of that validator.
        """
        query_str = """
            SELECT V.validator_index, E.timestamp FROM eth2_validators V
            LEFT JOIN eth_staking_events_info S ON S.validator_index = V.validator_index
            LEFT JOIN history_events E ON
            E.identifier = S.identifier WHERE ? - (SELECT MAX(timestamp) FROM history_events WHERE identifier=S.identifier) > ? AND S.validator_index IS NOT NULL
            AND E.entry_type=? GROUP BY V.validator_index HAVING MAX(E.timestamp)
            UNION
            SELECT DISTINCT V2.validator_index, 0 FROM eth2_validators V2 WHERE
            V2.validator_index NOT IN (
                SELECT validator_index FROM eth_staking_events_info S2 LEFT JOIN
                history_events E2 ON S2.identifier=E2.identifier WHERE E2.entry_type=?
            )
        """  # noqa: E501
        with self.db.conn.read_ctx() as cursor:
            result = cursor.execute(
                query_str,
                (up_to_tsms, WITHDRAWALS_RECHECK_PERIOD, HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT.serialize_for_db(), HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT.serialize_for_db()),  # noqa: E501
            ).fetchall()
        return result

    def get_validators_to_query_for_stats(self, up_to_ts: Timestamp) -> list[tuple[int, Timestamp]]:  # noqa: E501
        """Gets a list of validators that need to be queried for new daily stats

        Validators need to be queried if last time they are queried was more than 2 days.

        Returns a list of tuples. First entry is validator index and second entry is
        last queried timestamp for daily stats of that validator.
        """
        query_str = """
            SELECT D.validator_index, D.timestamp FROM eth2_validators V LEFT JOIN
            eth2_daily_staking_details D ON
            V.validator_index = D.validator_index AND ? - (SELECT MAX(timestamp) FROM eth2_daily_staking_details WHERE validator_index=V.validator_index) > ? WHERE D.validator_index IS NOT NULL AND D.timestamp==(SELECT MAX(timestamp) FROM eth2_daily_staking_details WHERE validator_index=V.validator_index)
            UNION
            SELECT DISTINCT V2.validator_index, 0 FROM eth2_validators V2 WHERE
            V2.validator_index NOT IN (SELECT validator_index FROM eth2_daily_staking_details)
        """  # noqa: E501
        with self.db.conn.read_ctx() as cursor:
            result = cursor.execute(
                query_str,
                # 2 days since stats page only appears once day is over. So if today is
                # 27/10 19:46 the last full day it has is 26/10 00:00, which is more than a day
                # but less than 2
                (up_to_ts, DAY_IN_SECONDS * 2 + 1),
            ).fetchall()
        return result

    def add_validator_daily_stats(self, stats: list[ValidatorDailyStats]) -> None:
        """Adds given daily stats for validator in the DB. If an entry exists it's skipped"""
        for entry in stats:  # not doing executemany to just ignore existing entry
            try:
                with self.db.user_write() as write_cursor:
                    write_cursor.execute(
                        'INSERT INTO eth2_daily_staking_details(validator_index, timestamp, pnl) '
                        'VALUES(?,?,?)',
                        entry.to_db_tuple(),
                    )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                log.debug(
                    f'Cant insert Eth2 staking detail entry {str(entry)} to the DB '
                    f'due to {str(e)}. Skipping ...',
                )

    def get_validator_daily_stats_and_limit_info(
            self,
            cursor: 'DBCursor',
            filter_query: 'Eth2DailyStatsFilterQuery',
    ) -> tuple[list[ValidatorDailyStats], int]:
        """Gets all eth2 daily stats for the query from the DB

        Returns a tuple with the following in order:
         - A list of the daily stats
         - How many are the total entries found for the filter
        """
        stats = self.get_validator_daily_stats(cursor, filter_query=filter_query)
        query, bindings = filter_query.prepare(with_pagination=False)
        query = 'SELECT COUNT(*) from eth2_daily_staking_details ' + query
        count = cursor.execute(query, bindings).fetchone()[0]
        return stats, count

    def get_validator_daily_stats(
            self,
            cursor: 'DBCursor',
            filter_query: 'Eth2DailyStatsFilterQuery',
    ) -> list[ValidatorDailyStats]:
        """Gets all DB entries for validator daily stats according to the given filter"""
        query, bindings = filter_query.prepare()
        query = 'SELECT * from eth2_daily_staking_details ' + query
        cursor.execute(query, bindings)
        daily_stats = [ValidatorDailyStats.deserialize_from_db(x) for x in cursor]
        # Take into account the proportion of the validator owned
        validators_ownership = {
            validator.index: validator.ownership_proportion
            for validator in self.get_validators(cursor)
        }
        for daily_stat in daily_stats:
            owned_proportion = validators_ownership.get(daily_stat.validator_index, ONE)
            if owned_proportion != ONE:
                daily_stat.pnl = daily_stat.pnl * owned_proportion
        return daily_stats

    def validator_exists(
            self,
            cursor: 'DBCursor',
            field: Literal['validator_index', 'public_key'],
            arg: Union[int, str],
    ) -> bool:
        cursor.execute(f'SELECT COUNT(*) from eth2_validators WHERE {field}=?', (arg,))
        return cursor.fetchone()[0] == 1  # count always returns

    def get_validators(self, cursor: 'DBCursor') -> list[Eth2Validator]:
        cursor.execute('SELECT * from eth2_validators;')
        return [Eth2Validator.deserialize_from_db(x) for x in cursor]

    def get_exited_validator_indices(self, cursor: 'DBCursor') -> set[int]:
        """Returns the indices of the tracked validators that we know have exited

        Does so by processing events, so will only return a list as up to date as the events we got
        """
        cursor.execute(
            'SELECT validator_index FROM eth_staking_events_info WHERE is_exit_or_blocknumber=1',
        )  # checking against literal 1 is safe since block 1 was not mined during PoS
        return {x[0] for x in cursor}

    def add_validators(self, write_cursor: 'DBCursor', validators: list[Eth2Validator]) -> None:  # noqa: E501
        write_cursor.executemany(
            'INSERT OR IGNORE INTO '
            'eth2_validators(validator_index, public_key, ownership_proportion) VALUES(?, ?, ?)',
            [x.serialize_for_db() for x in validators],
        )

    def edit_validator(self, validator_index: int, ownership_proportion: FVal) -> None:
        """Edits the ownership proportion for a validator identified by its index.
        May raise:
        - InputError if we try to edit a non existing validator.
        """
        with self.db.user_write() as cursor:
            cursor.execute(
                'UPDATE eth2_validators SET ownership_proportion=? WHERE validator_index = ?',
                (str(ownership_proportion), validator_index),
            )
            if cursor.rowcount == 0:
                raise InputError(
                    f'Tried to edit validator with index {validator_index} '
                    f'that is not in the database',
                )

    def delete_validators(self, validator_indices: list[int]) -> None:
        """Deletes the given validators from the DB. Due to marshmallow here at least one
        of the two arguments is not None.

        Also delete all events where that validator index is involved.

        May raise:
        - InputError if any of the given validators to delete does not exist in the DB
        """
        indices_num = len(validator_indices)
        question_marks = ['?'] * indices_num
        with self.db.user_write() as cursor:
            # Delete from the validators table. This should also delete from daily_staking_details
            cursor.execute(
                f'DELETE FROM eth2_validators WHERE validator_index IN '
                f'({",".join(question_marks)})',
                validator_indices,
            )
            if cursor.rowcount != len(validator_indices):
                raise InputError(
                    f'Tried to delete eth2 validator/s with indices {validator_indices} '
                    f'from the DB but at least one of them did not exist',
                )

            # Delete from the events table, all staking events except for deposits.
            # We keep deposits since they are associated with the address and are EVM transactions
            cursor.execute(
                f'DELETE FROM history_events WHERE identifier in (SELECT S.identifier '
                f'FROM eth_staking_events_info S WHERE S.validator_index IN '
                f'({",".join(question_marks)})) AND entry_type != ?',
                (*validator_indices, HistoryBaseEntryType.ETH_DEPOSIT_EVENT.serialize_for_db()),
            )

    @staticmethod
    def _validator_stats_process_queries(
            cursor: 'DBCursor',
            filter_query: EthStakingEventFilterQuery,
    ) -> FVal:
        """Execute DB query and extract numerical value after using filter_query"""
        base_query = 'SELECT SUM(CAST(amount AS REAL)) ' + ETH_STAKING_EVENT_JOIN
        query, bindings = filter_query.prepare(with_pagination=False)
        cursor.execute(base_query + query, bindings)
        if (amount := cursor.fetchone()[0]) is not None:
            return FVal(amount)

        return ZERO

    def get_validators_profit(
            self,
            withdrawals_filter_query: EthStakingEventFilterQuery,
            execution_filter_query: EthStakingEventFilterQuery,
    ) -> tuple[FVal, FVal]:
        """Query profit as sum of withdrawn ETH and rewards for block production and mev"""
        with self.db.conn.read_ctx() as cursor:
            withdrawals_amount = self._validator_stats_process_queries(cursor=cursor, filter_query=withdrawals_filter_query)  # noqa: E501
            execution_rewards_amount = self._validator_stats_process_queries(cursor=cursor, filter_query=execution_filter_query)  # noqa: E501

        return withdrawals_amount, execution_rewards_amount
