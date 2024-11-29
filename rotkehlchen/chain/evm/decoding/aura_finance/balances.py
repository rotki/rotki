import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.utils import get_token
from rotkehlchen.chain.ethereum.interfaces.balances import BalancesSheetType, ProtocolWithBalance
from rotkehlchen.chain.ethereum.utils import token_normalized_value_decimals
from rotkehlchen.chain.evm.constants import DEFAULT_TOKEN_DECIMALS
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.decoding.aura_finance.constants import CPT_AURA_FINANCE
from rotkehlchen.chain.evm.decoding.aura_finance.utils import get_aura_pool_price, query_aura_pools
from rotkehlchen.chain.evm.tokens import get_chunk_size_call_order
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress

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
            deposit_event_types={
                (HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET),
            },
        )

    def query_balances(self) -> BalancesSheetType:
        try:
            query_aura_pools(self.evm_inquirer)
        except RemoteError as e:
            log.error(
                f'Failed to query Aura pools on {self.evm_inquirer.chain_name}: {e!s}. '
                'Continuing with existing pools data.',
            )

        balances: BalancesSheetType = defaultdict(BalanceSheet)
        addresses_with_activities = self.addresses_with_activity(event_types={
            (HistoryEventType.RECEIVE, HistoryEventSubType.RECEIVE_WRAPPED),
        })
        pools: set[ChecksumEvmAddress] = set()
        if len(addresses_with_deposits := list(addresses_with_activities.keys())) == 0:
            return balances

        for events in addresses_with_activities.values():
            pools.update(event.asset.resolve_to_evm_token().evm_address for event in events)

        chunk_size, call_order = get_chunk_size_call_order(self.evm_inquirer)
        for pool in pools:
            try:
                pool_contract = EvmContract(
                    address=pool,
                    abi=self.evm_inquirer.contracts.abi('ERC20_TOKEN'),
                    deployed_block=0,
                )
                results = self.evm_inquirer.multicall(
                    calls=[
                        (
                            pool,
                            pool_contract.encode(
                                method_name='balanceOf',
                                arguments=[address],
                            ),
                        ) for address in addresses_with_deposits
                    ],
                    call_order=call_order,
                    calls_chunk_size=chunk_size,
                )
                if not results:
                    log.error(f'Failed to query aura finance balances for pool {pool_contract.address}')  # noqa: E501
                    continue

                for idx, result in enumerate(results):
                    user_address = addresses_with_deposits[idx]
                    if (balance := pool_contract.decode(
                        result=result,
                        method_name='balanceOf',
                        arguments=[user_address],
                    )[0]) == 0:
                        continue

                    formatted_balance = token_normalized_value_decimals(
                        token_amount=balance,
                        token_decimals=DEFAULT_TOKEN_DECIMALS,
                    )
                    if (aura_pool_token := get_token(
                        evm_address=pool_contract.address,
                        chain_id=self.evm_inquirer.chain_id,
                    )) is None:
                        log.error(
                            f'No cached token found for pool {pool_contract.address} '
                            f'on {self.evm_inquirer.chain_name}',
                        )
                        continue

                    price = get_aura_pool_price(
                        token=aura_pool_token,
                        inquirer=Inquirer(),
                    )
                    balances[user_address].assets[aura_pool_token] += Balance(
                        amount=formatted_balance,
                        usd_value=formatted_balance * price,
                    )
            except (RemoteError, IndexError, ValueError) as e:
                log.error(
                    f'Failed to query {CPT_AURA_FINANCE} balances for pool {pool} on '
                    f'{self.evm_inquirer.chain_name} due to {e!s}',
                )
                continue

        return balances
