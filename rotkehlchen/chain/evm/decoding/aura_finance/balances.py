import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.aura_finance.constants import CPT_AURA_FINANCE
from rotkehlchen.chain.evm.decoding.aura_finance.utils import get_aura_pool_price
from rotkehlchen.chain.evm.tokens import get_chunk_size_call_order
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.assets.asset import EvmToken
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class AuraFinanceBalances(ProtocolWithBalance):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
    ):
        super().__init__(
            tx_decoder=tx_decoder,
            counterparty=CPT_AURA_FINANCE,
            evm_inquirer=evm_inquirer,
            deposit_event_types=set(),
        )

    def query_balances(self) -> BalancesSheetType:
        balances: BalancesSheetType = defaultdict(BalanceSheet)
        addresses_with_activities = self.addresses_with_activity(event_types={
            (HistoryEventType.RECEIVE, HistoryEventSubType.RECEIVE_WRAPPED),
        })
        active_addresses = []
        pools: set[EvmToken] = set()
        for address, events in addresses_with_activities.items():
            active_addresses.append(address)
            pools.update(event.asset.resolve_to_evm_token() for event in events)

        if len(active_addresses) == 0 or len(pools) == 0:
            return balances

        chunk_size, call_order = get_chunk_size_call_order(self.evm_inquirer)
        erc20_abi = self.evm_inquirer.contracts.abi('ERC20_TOKEN')
        for pool_token in pools:
            try:
                pool_contract = EvmContract(
                    address=pool_token.evm_address,
                    abi=erc20_abi,
                    deployed_block=0,  # unused in this context
                )
                results = self.evm_inquirer.multicall(
                    calls=[
                        (
                            pool_token.evm_address,
                            pool_contract.encode(
                                method_name='balanceOf',
                                arguments=[address],
                            ),
                        ) for address in active_addresses
                    ],
                    call_order=call_order,
                    calls_chunk_size=chunk_size,
                )
                if not results:
                    log.error(f'Failed to query {self.evm_inquirer.chain_name} aura finance balances for pool {pool_contract.address}')  # noqa: E501
                    continue

                for idx, result in enumerate(results):
                    user_address = active_addresses[idx]
                    if (balance := pool_contract.decode(
                        result=result,
                        method_name='balanceOf',
                        arguments=[user_address],
                    )[0]) == 0:
                        continue

                    formatted_balance = asset_normalized_value(
                        amount=balance,
                        asset=pool_token,
                    )
                    price = get_aura_pool_price(
                        token=pool_token,
                        inquirer=Inquirer(),
                    )
                    balances[user_address].assets[pool_token] += Balance(
                        amount=formatted_balance,
                        usd_value=formatted_balance * price,
                    )
            except (RemoteError, IndexError, ValueError) as e:
                log.error(
                    f'Failed to query aura finance balances for pool {pool_token.evm_address} on '
                    f'{self.evm_inquirer.chain_name} due to {e!s}',
                )
                continue

        return balances
