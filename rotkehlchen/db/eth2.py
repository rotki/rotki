import logging
from typing import TYPE_CHECKING, Final, Literal

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.chain.ethereum.modules.eth2.structures import (
    ValidatorDailyStats,
    ValidatorDetails,
    ValidatorDetailsWithStatus,
)
from rotkehlchen.chain.ethereum.modules.eth2.utils import form_withdrawal_notes
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS, HOUR_IN_SECONDS
from rotkehlchen.db.filtering import (
    ETH_STAKING_EVENT_JOIN,
    EthStakingEventFilterQuery,
    EthWithdrawalFilterQuery,
)
from rotkehlchen.errors.misc import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress, Eth2PubKey, Timestamp
from rotkehlchen.utils.misc import ts_ms_to_sec, ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.client import DBCursor, DBWriterClient
    from rotkehlchen.db.filtering import Eth2DailyStatsFilterQuery

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


# At the moment of writing the moment between queing a withdrawal and it happpening seems to be 8-9 days  # noqa: E501
TEMP_MAX_WITHDRAWAL_WAIT: Final = DAY_IN_SECONDS * 9


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
                # stats page entry only appears once day is over and some times it takes
                # a longer time to update since it counts beacon chain days.
                # So we will put two days and more than half to be sure we don't
                # query too often
                (up_to_ts, DAY_IN_SECONDS * 2 + HOUR_IN_SECONDS * 18),
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
         - How many are the total entries found for the filter (ignoring pagination)
         - Sum of ETH gained/lost for the filter
        """
        stats = self.get_validator_daily_stats(cursor, filter_query=filter_query)
        query, bindings = filter_query.prepare(with_pagination=False)
        # TODO: A weakness of this query is that it does not take into account the
        # ownership proportion of the validator in the PnL here
        query = f'SELECT COUNT(*), SUM(pnl) FROM (SELECT * FROM  eth2_daily_staking_details {query})'  # noqa: E501
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
        validators_ownership = self.get_index_to_ownership(cursor)
        for daily_stat in daily_stats:
            owned_proportion = validators_ownership.get(daily_stat.validator_index, ONE)
            if owned_proportion != ONE:
                daily_stat.pnl *= owned_proportion
        return daily_stats

    def validator_exists(
            self,
            cursor: 'DBCursor',
            field: Literal['validator_index', 'public_key'],
            arg: int | Eth2PubKey,
    ) -> bool:
        cursor.execute(f'SELECT COUNT(*) from eth2_validators WHERE {field}=?', (arg,))
        return cursor.fetchone()[0] == 1  # count always returns

    def get_pubkey_to_ownership(self, cursor: 'DBCursor') -> dict[Eth2PubKey, FVal]:
        return {x[0]: FVal(x[1]) for x in cursor.execute('SELECT public_key, ownership_proportion FROM eth2_validators')}  # noqa: E501

    def get_index_to_ownership(self, cursor: 'DBCursor') -> dict[int, FVal]:
        return {x[0]: FVal(x[1]) for x in cursor.execute('SELECT validator_index, ownership_proportion FROM eth2_validators WHERE validator_index IS NOT NULL')}  # noqa: E501

    def get_validators(self, cursor: 'DBCursor') -> list[ValidatorDetails]:
        cursor.execute(
            'SELECT validator_index, public_key, ownership_proportion, withdrawal_address, '
            'activation_timestamp, withdrawable_timestamp FROM eth2_validators;',
        )
        return [ValidatorDetails.deserialize_from_db(x) for x in cursor]

    def get_validators_with_status(
            self,
            cursor: 'DBCursor',
            validator_indices: set[int] | None,
    ) -> list[ValidatorDetailsWithStatus]:
        result: list[ValidatorDetailsWithStatus] = []
        exited_indices = self.get_exited_validator_indices(cursor)
        cursor.execute(
            'SELECT validator_index, public_key, ownership_proportion, withdrawal_address, '
            'activation_timestamp, withdrawable_timestamp FROM eth2_validators;',
        )
        for entry in cursor:
            validator = ValidatorDetailsWithStatus.deserialize_from_db(entry)
            validator.determine_status(exited_indices)
            result.append(validator)

        if validator_indices is not None:
            result = [x for x in result if x.validator_index is not None and x.validator_index in validator_indices]  # noqa: E501

        return result

    def get_active_validator_indices(self, cursor: 'DBCursor') -> set[int]:
        """Returns the indices of the tracked validators that we know have not exited

        Same issues as with the get_exited_validator_indices function as far as
        using processed events is concerned.
        """
        cursor.execute(
            'SELECT validator_index from eth2_validators WHERE withdrawable_timestamp IS NULL '
            'OR (? - withdrawable_timestamp < ?)',
            (ts_now(), TEMP_MAX_WITHDRAWAL_WAIT),
        )
        result = {x[0] for x in cursor}
        return result

    def get_exited_validator_indices(self, cursor: 'DBCursor') -> set[int]:
        """Returns the indices of the tracked validators that we know have exited

        This used to query the eth staking events for full exit of the validator

        But since https://github.com/rotki/rotki/issues/8397 we need to change strategy and
        for now we just compare withdrawable_ts with current timetamp. If the difference
        is "big enough" we consider it exited.

        The reason is that we don't always track the withdrawal address such as for eigenlayer
        and we still need to know that a validator exited.

        This solution is hacky. As per the linked issue the actual solution will come
        in develop/1.35.0
        """
        cursor.execute(
            'SELECT validator_index FROM eth2_validators WHERE withdrawable_timestamp '
            'IS NOT NULL AND ? - withdrawable_timestamp > ?',
            (ts_now(), TEMP_MAX_WITHDRAWAL_WAIT),
        )
        result = {x[0] for x in cursor}
        return result

    def get_associated_with_addresses_validator_indices(
            self,
            cursor: 'DBCursor',
            addresses: list[ChecksumEvmAddress],
    ) -> set[int]:
        """Returns indices of validators that are associated with the given addresses.

        Association means either it's a withdrawal address for any validator or
        has been used as a fee recipient for a validator or deposited to a validator.
        """
        questionmarks = '?' * len(addresses)
        cursor.execute(
            f'SELECT S.validator_index FROM eth_staking_events_info S LEFT JOIN '
            f'history_events H on S.identifier=H.identifier WHERE H.location_label IN '
            f'({",".join(questionmarks)})', addresses,
        )
        return {x[0] for x in cursor}

    def set_validator_exit(
            self,
            write_cursor: 'DBWriterClient',
            index: int,
            withdrawable_timestamp: Timestamp,
    ) -> None:
        """If the validator has withdrawal events, find last one and mark as exit if after withdrawable ts"""  # noqa: E501
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT HE.identifier, HE.timestamp, HE.amount FROM history_events HE LEFT JOIN '
                'eth_staking_events_info SE ON SE.identifier = HE.identifier WHERE '
                'SE.validator_index=? AND HE.entry_type=? ORDER BY HE.timestamp DESC LIMIT 1',
                (index, HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT.value),
            )
            if (latest_result := cursor.fetchone()) is None:
                return  # no event found so nothing to do

        if ts_ms_to_sec(latest_result[1]) >= withdrawable_timestamp:
            write_cursor.execute(
                'UPDATE eth_staking_events_info SET is_exit_or_blocknumber=? WHERE identifier=?',
                (1, latest_result[0]),
            )
            write_cursor.execute(
                'UPDATE history_events SET notes=? WHERE identifier=?',
                (form_withdrawal_notes(is_exit=True, validator_index=index, amount=latest_result[2]), latest_result[0]),  # noqa: E501
            )

    def add_or_update_validators_except_ownership(
            self,
            write_cursor: 'DBWriterClient',
            validators: list[ValidatorDetails],
    ) -> None:
        """Adds or update validator data but keeps the ownership already in the DB"""
        self.add_or_update_validators(
            write_cursor=write_cursor,
            validators=validators,
            updatable_attributes=('validator_index', 'withdrawal_address', 'activation_timestamp', 'withdrawable_timestamp'),  # noqa: E501
        )

    def add_or_update_validators(
            self,
            write_cursor: 'DBWriterClient',
            validators: list[ValidatorDetails],
            updatable_attributes: tuple[str, ...] = ('validator_index', 'ownership_proportion', 'withdrawal_address', 'activation_timestamp', 'withdrawable_timestamp'),  # noqa: E501
    ) -> None:
        """Adds or updates validator data

        This used to do an INSERT OR REPLACE with an executemany. While that approach
        was simpler and "worked" it also killed all foreign key relations and since
        at the time of writing the daily stats have a foreign key relation to this table
        all the daily stats were deleted.
        """
        with self.db.conn.read_ctx() as cursor:
            for validator in validators:
                result = cursor.execute(
                    'SELECT validator_index, public_key, ownership_proportion, '
                    'withdrawal_address, activation_timestamp, withdrawable_timestamp FROM '
                    'eth2_validators WHERE public_key=?', (validator.public_key,),
                ).fetchone()
                if result is not None:  # update case
                    db_validator = ValidatorDetails.deserialize_from_db(result)
                    for attr in updatable_attributes:
                        if getattr(db_validator, attr) != (new_value := getattr(validator, attr)):
                            write_cursor.execute(
                                f'UPDATE eth2_validators SET {attr}=? WHERE public_key=?',
                                (new_value, validator.public_key),
                            )
                else:  # insertion case
                    write_cursor.execute(
                        'INSERT INTO '
                        'eth2_validators(validator_index, public_key, ownership_proportion, withdrawal_address, activation_timestamp, withdrawable_timestamp) VALUES(?, ?, ?, ?, ?, ?)',  # noqa: E501
                        validator.serialize_for_db(),
                    )

    def edit_validator_ownership(self, write_cursor: 'DBWriterClient', validator_index: int, ownership_proportion: FVal) -> None:  # noqa: E501
        """Edits the ownership proportion for a validator identified by its index.
        May raise:
        - InputError if we try to edit a non existing validator.
        """
        write_cursor.execute(
            'UPDATE eth2_validators SET ownership_proportion=? WHERE validator_index = ?',
            (str(ownership_proportion), validator_index),
        )
        if write_cursor.rowcount == 0:
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
            amount_querystr: str,
            filter_query: EthStakingEventFilterQuery,
    ) -> dict[int, FVal]:
        """Execute DB query and extract numerical value per validator after using filter_query

        Return a dict of validator index to sum of amounts per validator in the filter
        """
        base_query = f'SELECT validator_index, {amount_querystr} ' + ETH_STAKING_EVENT_JOIN
        query, bindings = filter_query.prepare(with_pagination=False, with_order=False)
        cursor.execute(base_query + query + ' GROUP BY eth_staking_events_info.validator_index', bindings)  # noqa: E501

        return {entry[0]: FVal(entry[1]) for entry in cursor}

    def get_validators_profit(
            self,
            cursor: 'DBCursor',
            withdrawals_filter_query: EthWithdrawalFilterQuery,
            exits_filter_query: EthWithdrawalFilterQuery,
            execution_filter_query: EthStakingEventFilterQuery,
    ) -> tuple[dict[int, FVal], dict[int, FVal], dict[int, FVal]]:
        """Query withdrawals, exits, EL rewards amounts for the given filter.

        Returns each of the different amount sums for the period per validator
        """
        withdrawals_amounts = self._validator_stats_process_queries(
            cursor=cursor,
            amount_querystr='SUM(CAST(amount AS REAL))',
            filter_query=withdrawals_filter_query,
        )
        exits_pnl = self._validator_stats_process_queries(
            cursor=cursor,
            amount_querystr='CAST(amount AS REAL) - 32',
            filter_query=exits_filter_query,
        )
        execution_rewards_amounts = self._validator_stats_process_queries(
            cursor=cursor,
            amount_querystr='SUM(CAST(amount AS REAL))',
            filter_query=execution_filter_query,
        )
        return withdrawals_amounts, exits_pnl, execution_rewards_amounts
