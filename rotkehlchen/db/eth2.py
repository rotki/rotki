import logging
from typing import TYPE_CHECKING, Literal, Union

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.accounting.structures.base import HistoryBaseEntryType
from rotkehlchen.chain.ethereum.modules.eth2.structures import Eth2Validator, ValidatorDailyStats
from rotkehlchen.chain.ethereum.modules.eth2.utils import form_withdrawal_notes, timestamp_to_epoch
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.filtering import ETH_STAKING_EVENT_JOIN, EthStakingEventFilterQuery
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import Timestamp
from rotkehlchen.utils.misc import ts_ms_to_sec

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor
    from rotkehlchen.db.filtering import Eth2DailyStatsFilterQuery

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# How much time more than the last time a withdrawal happened to have allowed to pass
# in order to recheck withdrawals for a given validator. In average at time of writing
# withdrawals occur every 4-7 days for a single validator
WITHDRAWALS_RECHECK_PERIOD = 4 * DAY_IN_SECONDS * 1000  # 4 days in milliseconds


class DBEth2:

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def get_validators_to_query_for_stats(self, up_to_ts: Timestamp) -> list[tuple[int, Timestamp, Timestamp]]:  # noqa: E501
        """Gets a list of validators that need to be queried for new daily stats

        Validators need to be queried if last time they are queried was more than 2 days.

        Returns a list of tuples. First entry is validator index, second entry is
        last queried timestamp for daily stats of that validator and third one is
        an optional timestamp of the validator's exit.
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
            stats_data = cursor.execute(
                query_str,
                # 2 days since stats page only appears once day is over. So if today is
                # 27/10 19:46 the last full day it has is 26/10 00:00, which is more than a day
                # but less than 2
                (up_to_ts, DAY_IN_SECONDS * 2 + 1),
            ).fetchall()
            exited_data = {}
            cursor.execute(
                'SELECT S.validator_index, H.timestamp FROM eth_staking_events_info S '
                'LEFT JOIN history_events H ON S.identifier=H.identifier '
                'WHERE S.is_exit_or_blocknumber=1',
            )
            for entry in cursor:
                exited_data[entry[0]] = ts_ms_to_sec(entry[1])

        result = []
        for data in stats_data:
            exit_ts = exited_data.get(data[0])
            if exit_ts is not None and exit_ts <= data[1]:
                # skip query for validators that exited and last stats is around exit
                continue

            result.append(data + (exit_ts,))

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
                    f'Cant insert Eth2 staking detail entry {entry!s} to the DB '
                    f'due to {e!s}. Skipping ...',
                )

    def get_validator_daily_stats_and_limit_info(
            self,
            cursor: 'DBCursor',
            filter_query: 'Eth2DailyStatsFilterQuery',
    ) -> tuple[list[ValidatorDailyStats], int, FVal]:
        """Gets all eth2 daily stats for the query from the DB

        Returns a tuple with the following in order:
         - A list of the daily stats
         - How many are the total entries found for the filter
         - Sum of ETH gained/lost for the filter
        """
        stats = self.get_validator_daily_stats(cursor, filter_query=filter_query)
        query, bindings = filter_query.prepare(with_pagination=False)
        # TODO: A weakness of this query is that it does not take into account the
        # ownership proportion of the validator in the PnL here
        query = 'SELECT COUNT(*), SUM(pnl) from eth2_daily_staking_details ' + query
        count, eth_sum_str = cursor.execute(query, bindings).fetchone()
        return stats, count, FVal(eth_sum_str) if eth_sum_str is not None else ZERO

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

    def get_active_validator_indices(self, cursor: 'DBCursor') -> set[int]:
        """Returns the indices of the tracked validators that we know have not exited

        Does so by using processed events, so will only return a list as up to date
        as the events we got
        """
        cursor.execute(
            'SELECT EV.validator_index FROM eth2_validators EV LEFT JOIN '
            'eth_staking_events_info SE ON EV.validator_index = SE.validator_index '
            'WHERE SE.validator_index IS NULL '
            'UNION '
            'SELECT DISTINCT EV.validator_index FROM eth2_validators EV INNER JOIN '
            'eth_staking_events_info SE ON EV.validator_index = SE.validator_index '
            'WHERE EV.validator_index NOT IN ('
            'SELECT validator_index from eth_staking_events_info WHERE is_exit_or_blocknumber=1)',
        )
        return {x[0] for x in cursor}

    def get_exited_validator_indices(self, cursor: 'DBCursor') -> set[int]:
        """Returns the indices of the tracked validators that we know have exited

        Does so by using processed events, so will only return a list as up to date
        as the events we got
        """
        cursor.execute(
            'SELECT validator_index FROM eth_staking_events_info WHERE is_exit_or_blocknumber=1',
        )  # checking against literal 1 is safe since block 1 was not mined during PoS
        return {x[0] for x in cursor}

    def set_validator_exit(self, write_cursor: 'DBCursor', index: int, exit_epoch: int) -> None:
        """If the validator has withdrawal events, find last one and mark as exit if after exit epoch"""  # noqa: E501
        write_cursor.execute(
            'SELECT HE.identifier, HE.timestamp, HE.amount FROM history_events HE LEFT JOIN '
            'eth_staking_events_info SE ON SE.identifier = HE.identifier '
            'WHERE SE.validator_index=? ORDER BY HE.timestamp DESC LIMIT 1',
            (index,),
        )
        if (latest_result := write_cursor.fetchone()) is None:
            return  # no event found so nothing to do

        if timestamp_to_epoch(ts_ms_to_sec(latest_result[1])) > exit_epoch:
            write_cursor.execute(
                'UPDATE eth_staking_events_info SET is_exit_or_blocknumber=? WHERE identifier=?',
                (1, latest_result[0]),
            )
            write_cursor.execute(
                'UPDATE history_events SET notes=? WHERE identifier=?',
                (form_withdrawal_notes(is_exit=True, validator_index=index, amount=latest_result[2]), latest_result[0]),  # noqa: E501
            )

    def add_validators(self, write_cursor: 'DBCursor', validators: list[Eth2Validator]) -> None:
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
