import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.utils import token_normalized_value_decimals
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.ethereum.modules.aave.constants import STK_AAVE_ADDR
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.decoding.aave.constants import CPT_AAVE
from rotkehlchen.chain.evm.tokens import get_chunk_size_call_order
from rotkehlchen.constants.assets import A_AAVE
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AaveBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            tx_decoder: 'EthereumTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_AAVE,
            deposit_event_types={(HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET)},
        )

    def query_balances(self) -> 'BalancesSheetType':
        """Queries and returns the balances sheet for staking events.

        Retrieves deposit events and calls staking contract to get the total rewards balance.
        That is how much AAVE is ready to be claimed as staking rewards. For how
        much AAVE is staked, that is the stkAAVE balance which should appear as
        part of balance queries and is 1-1 to AAVE."""
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        if len(addresses_with_deposits := list(self.addresses_with_deposits())) == 0:
            return balances

        staking_contract = self.evm_inquirer.contracts.contract(address=STK_AAVE_ADDR)
        chunk_size, call_order = get_chunk_size_call_order(self.evm_inquirer)
        if len(staked_rewards := self.evm_inquirer.multicall(
            calls=[(
                staking_contract.address,
                staking_contract.encode(
                    method_name='getTotalRewardsBalance',
                    arguments=[user],
                ),
            ) for user in addresses_with_deposits],
            call_order=call_order,
            calls_chunk_size=chunk_size,
        )) == 0:
            return balances

        token_price = Inquirer.find_usd_price(A_AAVE)
        for user, result in zip(addresses_with_deposits, staked_rewards, strict=True):
            balance: int
            if (balance := staking_contract.decode(
                result=result,
                method_name='getTotalRewardsBalance',
                arguments=[user],
            )[0]) == ZERO:
                continue

            if (balance_norm := token_normalized_value_decimals(
                token_amount=balance,
                token_decimals=DEFAULT_TOKEN_DECIMALS,
            )) > ZERO:
                balances[user].assets[A_AAVE][self.counterparty] += Balance(
                    amount=balance_norm,
                    usd_value=token_price * balance_norm,
                )

        return balances
