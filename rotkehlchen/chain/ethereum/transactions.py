import logging
from typing import List, Optional

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.db.ranges import DBQueryRanges
from rotkehlchen.errors import RemoteError
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ChecksumEthAddress, EthereumTransaction, Timestamp
from rotkehlchen.utils.interfaces import LockableQueryObject, protect_with_lock

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EthTransactions(LockableQueryObject):

    def __init__(self, database: DBHandler, etherscan: Etherscan) -> None:
        self.database = database
        self.etherscan = etherscan

    def _single_address_query_transactions(
            self,
            address: ChecksumEthAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> List[EthereumTransaction]:
        transactions = self.database.get_ethereum_transactions(
            from_ts=start_ts,
            to_ts=end_ts,
            address=address,
        )
        ranges = DBQueryRanges(self.database)
        ranges_to_query = ranges.get_location_query_ranges(
            location_string=f'ethtxs_{address}',
            start_ts=start_ts,
            end_ts=end_ts,
        )
        new_transactions = []
        for query_start_ts, query_end_ts in ranges_to_query:
            for internal in (False, True):
                try:
                    new_transactions.extend(self.etherscan.get_transactions(
                        account=address,
                        internal=False,
                        from_ts=query_start_ts,
                        to_ts=query_end_ts,
                    ))
                except RemoteError as e:
                    log.error(
                        f'Got error {str(e)} while querying ethereum transactions '
                        f'from Etherscan. Transactions not added to the DB',
                        from_ts=query_start_ts,
                        to_ts=query_end_ts,
                        internal=internal,
                    )

        # add new transactions to the DB
        if new_transactions != []:
            self.database.add_ethereum_transactions(new_transactions, from_etherscan=True)
        # and also set the last queried timestamps for the address
        ranges.update_used_query_range(
            location_string=f'ethtxs_{address}',
            start_ts=start_ts,
            end_ts=end_ts,
            ranges_to_query=ranges_to_query,
        )
        # finally append them to the already returned DB transactions
        transactions.extend(new_transactions)
        return transactions

    @protect_with_lock()
    def query(
            self,
            address: Optional[ChecksumEthAddress],
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> List[EthereumTransaction]:
        """Queries for all transactions (normal AND internal) of all ethereum accounts.
        Returns a list of all transactions of all accounts sorted by time.

        May raise:
        - RemoteError if etherscan is used and there is a problem with reaching it or
        with parsing the response.
        """
        transactions: List[EthereumTransaction] = []

        if address is not None:
            accounts = [address]
        else:
            accounts = self.database.get_blockchain_accounts().eth
        for address in accounts:
            transactions.extend(self._single_address_query_transactions(address, from_ts, to_ts))

        transactions.sort(key=lambda tx: tx.timestamp)
        return transactions
