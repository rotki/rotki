import logging
from typing import TYPE_CHECKING, List, Optional, Sequence

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.chain.ethereum.structures import Eth2Validator
from rotkehlchen.chain.ethereum.typing import Eth2Deposit, ValidatorDailyStats
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.timing import DAY_IN_SECONDS
from rotkehlchen.db.filtering import Eth2DailyStatsFilterQuery
from rotkehlchen.db.utils import form_query_to_filter_timestamps
from rotkehlchen.errors import InputError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ChecksumEthAddress, Timestamp, Tuple, Union

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

ETH2_DEPOSITS_PREFIX = 'eth2_deposits'

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DBEth2():

    def __init__(self, database: 'DBHandler') -> None:
        self.db = database

    def get_validators_to_query_for_stats(self, up_to_ts: Timestamp) -> List[Tuple[int, Timestamp]]:  # noqa: E501
        """Gets a list of validators that need to be queried for new daily stats

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
        cursor = self.db.conn.cursor()
        result = cursor.execute(
            query_str,
            (up_to_ts, DAY_IN_SECONDS),
        )
        return result.fetchall()

    def add_eth2_deposits(self, deposits: Sequence[Eth2Deposit]) -> None:
        """Inserts a list of Eth2Deposit"""
        query = (
            """
            INSERT INTO eth2_deposits (
                tx_hash,
                tx_index,
                from_address,
                timestamp,
                pubkey,
                withdrawal_credentials,
                amount,
                usd_value
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """
        )
        cursor = self.db.conn.cursor()
        for deposit in deposits:
            deposit_tuple = deposit.to_db_tuple()
            try:
                cursor.execute(query, deposit_tuple)
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                self.db.msg_aggregator.add_warning(
                    f'Failed to add an ETH2 deposit to the DB. Either a duplicate or  '
                    f'foreign key error.Deposit data: {deposit_tuple}. Error: {str(e)}',
                )
                continue

        self.db.update_last_write()

    def get_eth2_deposits(
            self,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            address: Optional[ChecksumEthAddress] = None,
    ) -> List[Eth2Deposit]:
        """Returns a list of Eth2Deposit filtered by time and address"""
        cursor = self.db.conn.cursor()
        query = (
            'SELECT '
            'tx_hash, '
            'tx_index, '
            'from_address, '
            'timestamp, '
            'pubkey, '
            'withdrawal_credentials, '
            'amount, '
            'usd_value '
            'FROM eth2_deposits '
        )
        # Timestamp filters are omitted, done via `form_query_to_filter_timestamps`
        filters = []
        if address is not None:
            filters.append(f'from_address="{address}" ')

        if filters:
            query += 'WHERE '
            query += 'AND '.join(filters)

        query, bindings = form_query_to_filter_timestamps(query, 'timestamp', from_ts, to_ts)
        results = cursor.execute(query, bindings)

        return [Eth2Deposit.deserialize_from_db(deposit_tuple) for deposit_tuple in results]

    def add_validator_daily_stats(self, stats: List[ValidatorDailyStats]) -> None:
        """Adds given daily stats for validator in the DB. If an entry exists it's skipped"""
        cursor = self.db.conn.cursor()
        for entry in stats:  # not doing executemany to just ignore existing entry
            try:
                cursor.execute(
                    'INSERT INTO eth2_daily_staking_details('
                    '    validator_index,'
                    '    timestamp,'
                    '    start_usd_price,'
                    '    end_usd_price,'
                    '    pnl,'
                    '    start_amount,'
                    '    end_amount,'
                    '    missed_attestations,'
                    '    orphaned_attestations,'
                    '    proposed_blocks,'
                    '    missed_blocks,'
                    '    orphaned_blocks,'
                    '    included_attester_slashings,'
                    '    proposer_attester_slashings,'
                    '    deposits_number,'
                    '    amount_deposited) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                    entry.to_db_tuple(),
                )
            except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
                log.debug(
                    f'Cant insert Eth2 staking detail entry {str(entry)} to the DB '
                    f'due to {str(e)}. Skipping ...',
                )

        self.db.update_last_write()

    def get_validator_daily_stats_and_limit_info(
            self,
            filter_query: Eth2DailyStatsFilterQuery,
    ) -> Tuple[List[ValidatorDailyStats], int, FVal, FVal]:
        """Gets all eth2 daily stats for the query from the DB

        Returns a tuple with the following in order:
         - A list of the daily stats
         - how many are the total found for the filter
         - What is the PnL in ETH for the filter
         - What is the sum of the usd_value of the PnL counting price at the time of each entry
        """
        stats = self.get_validator_daily_stats(filter_query=filter_query)
        cursor = self.db.conn.cursor()
        query, bindings = filter_query.prepare(with_pagination=False)
        query = (
            'SELECT COUNT(*), SUM(CAST(pnl AS REAL)), '
            'SUM(CAST(pnl AS REAL) * '
            '((CAST(start_usd_price AS REAL) + CAST(end_usd_price AS REAL)) / 2)) '
            'from eth2_daily_staking_details ' + query
        )
        result = cursor.execute(query, bindings).fetchone()
        try:
            pnl = FVal(result[1])
            usd_value_sum = FVal(result[2])
        except ValueError:
            pnl = ZERO
            usd_value_sum = ZERO

        return stats, result[0], pnl, usd_value_sum

    def get_validator_daily_stats(
            self,
            filter_query: Eth2DailyStatsFilterQuery,
    ) -> List[ValidatorDailyStats]:
        """Gets all DB entries for validator daily stats according to the given filter"""
        cursor = self.db.conn.cursor()
        query, bindings = filter_query.prepare()
        query = 'SELECT * from eth2_daily_staking_details ' + query
        results = cursor.execute(query, bindings)
        daily_stats = [ValidatorDailyStats.deserialize_from_db(x) for x in results]
        # Take into account the proportion of the validator owned
        validators_ownership = {
            validator.index: validator.ownership_proportion
            for validator in self.get_validators()
        }
        for daily_stat in daily_stats:
            owned_proportion = validators_ownership.get(daily_stat.validator_index, ONE)
            if owned_proportion != ONE:
                daily_stat.pnl = daily_stat.pnl * owned_proportion
        return daily_stats

    def validator_exists(self, field: str, arg: Union[int, str]) -> bool:
        cursor = self.db.conn.cursor()
        result = cursor.execute(f'SELECT COUNT(*) from eth2_validators WHERE {field}=?', (arg,))
        return result.fetchone()[0] == 1

    def get_validators(self) -> List[Eth2Validator]:
        cursor = self.db.conn.cursor()
        results = cursor.execute('SELECT * from eth2_validators;')
        return [Eth2Validator.deserialize_from_db(x) for x in results]

    def add_validators(self, validators: List[Eth2Validator]) -> None:
        cursor = self.db.conn.cursor()
        cursor.executemany(
            'INSERT OR IGNORE INTO '
            'eth2_validators(validator_index, public_key, ownership_proportion) VALUES(?, ?, ?)',
            [x.serialize_for_db() for x in validators],
        )
        self.db.update_last_write()

    def edit_validator(self, validator_index: int, ownership_proportion: FVal) -> None:
        """Edits the ownership proportion for a validator identified by its index.
        May raise:
        - InputError if we try to edit a non existing validator.
        """
        cursor = self.db.conn.cursor()
        cursor.execute(
            'UPDATE eth2_validators SET ownership_proportion=? WHERE validator_index = ?',
            (str(ownership_proportion), validator_index),
        )
        if cursor.rowcount == 0:
            raise InputError(
                f'Tried to edit validator with index {validator_index} '
                f'that is not in the database',
            )

    def delete_validator(self, validator_index: Optional[int], public_key: Optional[str]) -> None:
        """Deletes the given validator from the DB. Due to marshmallow here at least one
        of the two arguments is not None.

        May raise:
        - InputError if the given validator to delete does not exist in the DB
        """
        cursor = self.db.conn.cursor()
        if validator_index is not None:
            field = 'validator_index'
            input_tuple = (validator_index,)
        else:  # public key can't be None due to marshmallow
            field = 'public_key'
            input_tuple = (public_key,)  # type: ignore

        cursor.execute(f'DELETE FROM eth2_validators WHERE {field} == ?', input_tuple)
        if cursor.rowcount != 1:
            raise InputError(
                f'Tried to delete eth2 validator with {field} '
                f'{input_tuple[0]} from the DB but it did not exist',
            )
        self.db.update_last_write()
