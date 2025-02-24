from typing import TYPE_CHECKING, NamedTuple

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.constants import RAY
from rotkehlchen.chain.ethereum.defi.defisaver_proxy import HasDSProxy
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_DAI
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.premium.premium import Premium
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Price,
)

from .constants import RAD

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator


class DSRCurrentBalances(NamedTuple):
    balances: dict[ChecksumEvmAddress, Balance]
    # The percentage of the current DSR. e.g. 8% would be 8.00
    current_dsr: FVal


def _dsrdai_to_dai(value: int | FVal) -> FVal:
    """Turns a big integer that is the value of DAI in DSR into a proper DAI decimal FVal"""
    return FVal(value / FVal(RAD))


class MakerdaoDsr(HasDSProxy):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Premium | None,
            msg_aggregator: 'MessagesAggregator',
    ) -> None:

        super().__init__(
            ethereum_inquirer=ethereum_inquirer,
            database=database,
            premium=premium,
            msg_aggregator=msg_aggregator,
        )
        self.reset_last_query_ts()
        self.lock = Semaphore()
        self.dai = A_DAI.resolve_to_evm_token()
        self.makerdao_pot = self.ethereum.contracts.contract(string_to_evm_address('0x197E90f9FAD81970bA7976f33CbD77088E5D7cf7'))  # noqa: E501

    def reset_last_query_ts(self) -> None:
        """Reset the last query timestamps, effectively cleaning the caches"""
        self.ethereum.proxies_inquirer.reset_last_query_ts()

    def get_current_dsr(self) -> DSRCurrentBalances:
        """Gets the current DSR balance for all accounts that have DAI in DSR
        and the current DSR percentage

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result.
        - BlockchainQueryError if an ethereum node is used and the contract call
        queries fail for some reason
        """
        with self.lock:
            proxy_mappings = self.ethereum.proxies_inquirer.get_accounts_having_proxy()
            balances = {}
            try:
                current_dai_price = Inquirer.find_usd_price(A_DAI)
            except RemoteError:
                current_dai_price = Price(ONE)
            for account, proxy in proxy_mappings.items():
                guy_slice = self.makerdao_pot.call(self.ethereum, 'pie', arguments=[proxy])
                if guy_slice == 0:
                    # no current DSR balance for this proxy
                    continue
                chi = self.makerdao_pot.call(self.ethereum, 'chi')
                dai_balance = _dsrdai_to_dai(guy_slice * chi)
                balances[account] = Balance(
                    amount=dai_balance,
                    usd_value=current_dai_price * dai_balance,
                )

            current_dsr = self.makerdao_pot.call(self.ethereum, 'dsr')
            # Calculation is from here:
            # https://docs.makerdao.com/smart-contract-modules/rates-module#a-note-on-setting-rates
            current_dsr_percentage = ((FVal(current_dsr / RAY) ** 31622400) % 1) * 100
            return DSRCurrentBalances(balances=balances, current_dsr=current_dsr_percentage)
