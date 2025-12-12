from typing import TYPE_CHECKING, NamedTuple

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.constants import RAY
from rotkehlchen.chain.evm.proxies_inquirer import ProxyType
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
from rotkehlchen.utils.interfaces import EthereumModule

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


class MakerdaoDsr(EthereumModule):

    def __init__(
            self,
            ethereum_inquirer: 'EthereumInquirer',
            database: 'DBHandler',
            premium: Premium | None,
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        self.ethereum = ethereum_inquirer
        self.ethereum.proxies_inquirer.reset_last_query_ts()  # clean proxies cache at activation
        self.lock = Semaphore()
        self.dai = A_DAI.resolve_to_evm_token()
        self.makerdao_pot = self.ethereum.contracts.contract(string_to_evm_address('0x197E90f9FAD81970bA7976f33CbD77088E5D7cf7'))  # noqa: E501

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
            proxy_mappings = self.ethereum.proxies_inquirer.get_accounts_having_proxy(proxy_type=ProxyType.DS)  # noqa: E501
            balances = {}
            try:
                current_dai_price = Inquirer.find_main_currency_price(A_DAI)
            except RemoteError:
                current_dai_price = Price(ONE)
            for account, proxies in proxy_mappings.items():
                if len(proxies) == 0:
                    continue

                guy_slice = self.makerdao_pot.call(self.ethereum, 'pie', arguments=[next(iter(proxies))])  # noqa: E501
                if guy_slice == 0:
                    # no current DSR balance for this proxy
                    continue
                chi = self.makerdao_pot.call(self.ethereum, 'chi')
                dai_balance = _dsrdai_to_dai(guy_slice * chi)
                balances[account] = Balance(
                    amount=dai_balance,
                    value=current_dai_price * dai_balance,
                )

            current_dsr = self.makerdao_pot.call(self.ethereum, 'dsr')
            # Calculation is from here:
            # https://docs.makerdao.com/smart-contract-modules/rates-module#a-note-on-setting-rates
            current_dsr_percentage = ((FVal(current_dsr / RAY) ** 31622400) % 1) * 100
            return DSRCurrentBalances(balances=balances, current_dsr=current_dsr_percentage)

    # -- Methods following the EthereumModule interface -- #
    def on_account_addition(self, address: ChecksumEvmAddress) -> None:  # pylint: disable=useless-return
        ...

    def on_account_removal(self, address: ChecksumEvmAddress) -> None:
        ...

    def deactivate(self) -> None:
        ...
