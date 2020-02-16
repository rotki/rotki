import logging
from typing import Dict, List, Optional

from rotkehlchen.constants.ethereum import (
    MAKERDAO_PROXY_REGISTRY_ABI,
    MAKERDAO_PROXY_REGISTRY_ADDRESS,
)
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.ethchain import Ethchain
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ChecksumEthAddress, EthereumTransaction, Timestamp
from rotkehlchen.utils.misc import ts_now

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


class EthereumAnalyzer():
    """Analyzes ethereum chain data, like transactions, contract queries e.t.c."""
    def __init__(self, ethchain: Ethchain, database: DBHandler):
        self.ethchain = ethchain
        self.database = database
        self.last_run_ts = 0
        self.running = False

    def get_accounts_having_maker_proxy(self) -> Dict[ChecksumEthAddress, ChecksumEthAddress]:
        mapping = {}
        accounts = self.database.get_blockchain_accounts()
        for account in accounts.eth:
            result = self.ethchain.check_contract(
                contract_address=MAKERDAO_PROXY_REGISTRY_ADDRESS,
                abi=MAKERDAO_PROXY_REGISTRY_ABI,
                method_name='proxies',
                arguments=[account],
            )
            if int(result, 16) != 0:
                mapping[account] = result

        return mapping

    def _analyze_all_transactions(self) -> None:
        transactions = query_ethereum_transactions(
            database=self.database,
            etherscan=self.ethchain.etherscan,
            from_ts=0,
            to_ts=1581806659,  # 15/02/2020 23:44
        )

        for transaction in transactions:
            if transaction.to_address == '':  # Empty to_address is stored as '' for now
                # if empty to_address that means a contract was created
                continue

            # DO Something here

    def analyze_ethereum_transactions(self) -> None:
        if self.running:
            return

        if ts_now() - self.last_run_ts < 3600:
            return

        log.debug('Starting analysis')
        self.running = True
        mapping = self.get_accounts_having_maker_proxy()
        log.debug(f'----->{mapping}')

        self.running = False
        self.last_run_ts = ts_now()
