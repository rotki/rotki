import logging
from typing import List, Optional

from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import EthereumTransaction, Timestamp

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def query_ethereum_transactions(
        database: DBHandler,
        etherscan: Etherscan,
        from_ts: Optional[Timestamp] = None,
        to_ts: Optional[Timestamp] = None,
) -> List[EthereumTransaction]:
    """Queries for all transactions (normal AND internal) of all ethereum accounts.
    Returns a list of all transactions of all accounts sorted by time.

    May raise:
    - RemoteError if etherscan is used and there is a problem with reaching it or
    with parsing the response.
    """
    transactions: List[EthereumTransaction] = []

    accounts = database.get_blockchain_accounts()
    for address in accounts.eth:
        # If we already have any transactions in the DB for this from_address
        # from to_ts and on then that means the range has already been queried
        if to_ts:
            existing_txs = database.get_ethereum_transactions(from_ts=to_ts, address=address)
            if len(existing_txs) > 0:
                # So just query the DB only here
                transactions.extend(
                    database.get_ethereum_transactions(
                        from_ts=from_ts, to_ts=to_ts, address=address,
                    ),
                )
                continue

        # else we have to query etherscan for this address
        # TODO: Can we somehow shorten the query here by providing a block range?
        # Note: If we do, we then need to retrieve the rest of the transactions
        # from the DB.
        new_transactions = etherscan.get_transactions(account=address, internal=False)
        new_transactions.extend(etherscan.get_transactions(account=address, internal=True))

        # and finally also save the transactions in the DB
        database.add_ethereum_transactions(
            ethereum_transactions=new_transactions,
            from_etherscan=True,
        )
        transactions.extend(new_transactions)

    transactions.sort(key=lambda tx: tx.timestamp)
    return transactions
