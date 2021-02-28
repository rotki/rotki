from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.chain.ethereum.defi.structures import (
    DefiBalance,
    DefiProtocol,
    DefiProtocolBalances,
)
from rotkehlchen.chain.ethereum.defi.zerionsdk import ZerionSDK
from rotkehlchen.chain.ethereum.utils import multicall_specific, token_normalized_value_decimals
from rotkehlchen.constants.assets import A_CRV
from rotkehlchen.constants.ethereum import VOTE_ESCROWED_CRV
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.typing import ChecksumEthAddress, Price
from rotkehlchen.user_messages import MessagesAggregator

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.manager import EthereumManager


class DefiChad():
    """An aggregator for many things ethereum DeFi"""

    def __init__(
            self,
            ethereum_manager: 'EthereumManager',
            msg_aggregator: MessagesAggregator,
    ) -> None:
        self.ethereum = ethereum_manager
        self.zerion_sdk = ZerionSDK(ethereum_manager, msg_aggregator)

    def query_defi_balances(
            self,
            addresses: List[ChecksumEthAddress],
    ) -> Dict[ChecksumEthAddress, List[DefiProtocolBalances]]:
        defi_balances = defaultdict(list)
        for account in addresses:
            balances = self.zerion_sdk.all_balances_for_account(account)
            if len(balances) != 0:
                defi_balances[account] = balances

        # and also query balances of tokens that are not detected by zerion adapter contract
        result = multicall_specific(
            ethereum=self.ethereum,
            contract=VOTE_ESCROWED_CRV,
            method_name='locked',
            arguments=[[x] for x in addresses],
        )
        crv_price = Price(ZERO)
        if any(x[0] != 0 for x in result):
            crv_price = Inquirer().find_usd_price(A_CRV)
        for idx, address in enumerate(addresses):
            balance = result[idx][0]
            if balance == 0:
                continue
            # else the address has vote escrowed CRV
            amount = token_normalized_value_decimals(token_amount=balance, token_decimals=18)
            protocol_balance = DefiProtocolBalances(
                protocol=DefiProtocol(
                    name='Curve • Vesting',
                    description='Curve vesting or locked in escrow for voting',
                    url='https://www.curve.fi/',
                    version=1,
                ),
                balance_type='Asset',
                base_balance=DefiBalance(
                    token_address=VOTE_ESCROWED_CRV.address,
                    token_name='Vote-escrowed CRV',
                    token_symbol='veCRV',
                    balance=Balance(
                        amount=amount,
                        usd_value=amount * crv_price,
                    ),
                ),
                underlying_balances=[],
            )
            defi_balances[address].append(protocol_balance)

        return defi_balances
