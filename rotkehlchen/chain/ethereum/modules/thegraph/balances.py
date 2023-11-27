import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.interfaces.balances import ProtocolWithBalance
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.tokens import get_chunk_size_call_order
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_GRT
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import CONTRACT_STAKING, CPT_THEGRAPH

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.interfaces.balances import BalancesType
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import CHAIN_IDS_WITH_BALANCE_PROTOCOLS

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ThegraphBalances(ProtocolWithBalance):
    def __init__(
            self,
            database: DBHandler,
            evm_inquirer: 'EthereumInquirer',
            chain_id: 'CHAIN_IDS_WITH_BALANCE_PROTOCOLS',
    ):
        super().__init__(
            database=database,
            evm_inquirer=evm_inquirer,
            chain_id=chain_id,
            counterparty=CPT_THEGRAPH,
            deposit_event_types={(HistoryEventType.STAKING, HistoryEventSubType.DEPOSIT_ASSET)},
        )
        self.grt = A_GRT.resolve_to_evm_token()

    def query_balances(self) -> 'BalancesType':
        """
        Query balances of GRT tokens delegated to indexers if deposit events are found.
        First, the current shares amounts are fetched from the contract,
        then shares are converted into GRT balances according to the current pool ratio.
        The results include delegation rewards earned over time.
        """
        balances: BalancesType = defaultdict(lambda: defaultdict(Balance))

        # fetch deposit events
        addresses_with_deposits = self.addresses_with_deposits(products=[EvmProduct.STAKING])
        # remap all events into a list that will contain all pairs (delegator, indexer)
        delegations_unique = set()
        for delegator, event_list in addresses_with_deposits.items():
            for event in event_list:
                if event.extra_data is None:
                    continue
                if (indexer := event.extra_data.get('indexer')) is not None:
                    delegations_unique.add((delegator, indexer))
        delegations = list(delegations_unique)

        # user had no delegation events
        if len(delegations) == 0:
            return balances

        staking_contract = self.evm_inquirer.contracts.contract(string_to_evm_address(CONTRACT_STAKING))  # noqa: E501
        chunk_size, call_order = get_chunk_size_call_order(self.evm_inquirer)

        # query how many shares delegator currently have at the indexers/pools
        delegation_balances = self.evm_inquirer.multicall(
            calls=[(
                staking_contract.address,
                staking_contract.encode(
                    method_name='getDelegation',
                    arguments=[indexer, delegator],
                ),
            ) for delegator, indexer in delegations],
            call_order=call_order,
            calls_chunk_size=chunk_size,
        )

        # process all current delegation balances
        delegations_active = []
        for idx, delegation in enumerate(delegations):
            shares, _, _ = staking_contract.decode(
                delegation_balances[idx],
                'getDelegation',
                arguments=[delegation[1], delegation[0]],
            )[0]
            if shares > 0:
                delegations_active.append((delegation[0], delegation[1], shares))

        # user has already undelegated everything and has no active stakes
        if len(delegations_active) == 0:
            return balances

        # query current total amount of shares and tokens in all pools that currently have stake
        pools = self.evm_inquirer.multicall(
            calls=[(
                staking_contract.address,
                staking_contract.encode(
                    method_name='delegationPools',
                    arguments=[indexer],
                ),
            ) for _, indexer, _ in delegations_active],
            call_order=call_order,
            calls_chunk_size=chunk_size,
        )

        grt_price = Inquirer().find_usd_price(A_GRT)
        for idx, stake in enumerate(delegations_active):
            delegator, indexer, shares_amount = stake[0], stake[1], stake[2]

            # each calculation is for one pool
            _, _, _, _, pool_total_tokens, pool_total_shares = staking_contract.decode(
                result=pools[idx],
                method_name='delegationPools',
                arguments=[indexer],
            )[0]

            # calculate current tokens balance relative to the pool state and shares distribution
            if pool_total_shares == 0:
                continue
            balance = FVal(shares_amount * pool_total_tokens / pool_total_shares)
            balance_norm = asset_normalized_value(balance.to_int(exact=False), self.grt)
            balances[delegator][self.grt] += Balance(
                amount=balance_norm,
                usd_value=grt_price * balance_norm,
            )

        return balances
