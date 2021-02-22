from typing import TYPE_CHECKING, Dict, Optional

from eth_utils.address import to_checksum_address

from rotkehlchen.constants.ethereum import MAKERDAO_PROXY_REGISTRY
from rotkehlchen.premium.premium import Premium
from rotkehlchen.typing import ChecksumEthAddress
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.interfaces import EthereumModule
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager
    from rotkehlchen.db.dbhandler import DBHandler

MAKERDAO_REQUERY_PERIOD = 7200  # Refresh queries every 2 hours

WAD_DIGITS = 18
WAD = 10**WAD_DIGITS
RAY_DIGITS = 27
RAY = 10**RAY_DIGITS
RAD_DIGITS = 45
RAD = 10**RAD_DIGITS


class MakerdaoCommon(EthereumModule):
    """Class to manage MakerDao related stuff such as DSR and CDPs/Vaults"""

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            database: 'DBHandler',
            premium: Optional[Premium],
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.premium = premium
        self.ethereum = ethereum_manager
        self.database = database
        self.msg_aggregator = msg_aggregator
        self.proxy_mappings: Dict[ChecksumEthAddress, ChecksumEthAddress] = {}
        self.reset_last_query_ts()

    def reset_last_query_ts(self) -> None:
        """Reset the last query timestamps, effectively cleaning the caches"""
        self.last_proxy_mapping_query_ts = 0

    def _get_account_proxy(self, address: ChecksumEthAddress) -> Optional[ChecksumEthAddress]:
        """Checks if a DSR proxy exists for the given address and returns it if it does

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        result = MAKERDAO_PROXY_REGISTRY.call(self.ethereum, 'proxies', arguments=[address])
        if int(result, 16) != 0:
            return to_checksum_address(result)
        return None

    def _get_accounts_having_maker_proxy(self) -> Dict[ChecksumEthAddress, ChecksumEthAddress]:
        """Returns a mapping of accounts that have DSR proxies to their proxies

        If the proxy mappings have been queried in the past REQUERY_PERIOD
        seconds then the old result is used.

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        now = ts_now()
        if now - self.last_proxy_mapping_query_ts < MAKERDAO_REQUERY_PERIOD:
            return self.proxy_mappings

        mapping = {}
        accounts = self.database.get_blockchain_accounts()
        for account in accounts.eth:
            proxy_result = self._get_account_proxy(account)
            if proxy_result:
                mapping[account] = proxy_result

        self.last_proxy_mapping_query_ts = ts_now()
        self.proxy_mappings = mapping
        return mapping

    # -- Methods following the EthereumModule interface -- #
    def on_startup(self) -> None:
        pass

    def on_account_addition(self, address: ChecksumEthAddress) -> None:
        self.reset_last_query_ts()
        # Get the proxy of the account
        proxy_result = self._get_account_proxy(address)
        if proxy_result is None:
            return

        # add it to the mapping
        self.proxy_mappings[address] = proxy_result

    def on_account_removal(self, address: ChecksumEthAddress) -> None:
        self.reset_last_query_ts()

    def deactivate(self) -> None:
        pass
