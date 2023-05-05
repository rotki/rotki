import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmProduct
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.interfaces.balances import ProtocolWithBalance
from rotkehlchen.chain.ethereum.modules.curve.balances import query_gauges_balances
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.chain.evm.tokens import get_chunk_size_call_order
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_CVX
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

from .constants import CPT_CONVEX

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

BalancesType = dict[ChecksumEvmAddress, dict[EvmToken, Balance]]


class ConvexBalances(ProtocolWithBalance):
    """Query staked balances in the Convex gauges"""

    def __init__(self, database: DBHandler, evm_inquirer: 'EvmNodeInquirer'):
        super().__init__(database=database, evm_inquirer=evm_inquirer, counterparty=CPT_CONVEX)
        self.cvx = A_CVX.resolve_to_evm_token()

    def _query_staked_cvx(
            self,
            balances: BalancesType,
            staking_contract: EvmContract,
    ) -> None:
        """
        Query staking balances for CVX if there was a deposit event in Convex.
        The logic is the same for locked cvx and staked cvx that is why staking_contract
        is variable.
        The balances variable is mutated in this function.
        """
        addresses_with_stake_mapping = self.addresses_with_deposits(
            product=EvmProduct.STAKING,
            deposit_events={(HistoryEventType.DEPOSIT, HistoryEventSubType.NONE)},
        )
        # addresses_with_deposits returns a mapping of address to evm event but since we will call
        # the staking contracts with the addresses as arguments we need the list of addresses to
        # index them later
        addresses_with_stake = list(addresses_with_stake_mapping.keys())
        if len(addresses_with_stake) == 0:
            return None

        cvx_price = Inquirer().find_usd_price(self.cvx)
        try:
            call_output = self.evm_inquirer.multicall(
                calls=[(
                    staking_contract.address,
                    staking_contract.encode(method_name='balanceOf', arguments=[address]),
                ) for address in addresses_with_stake],
            )
        except RemoteError as e:
            log.error(f'Failed to query convex balances due to {str(e)}')
            return None

        for idx, result in enumerate(call_output):
            address = addresses_with_stake[idx]
            amount_raw = staking_contract.decode(result, 'balanceOf', arguments=[address])[0]
            amount = asset_normalized_value(amount_raw, self.cvx)
            if amount == ZERO:
                continue

            balance = Balance(amount=amount, usd_value=cvx_price * amount)
            balances[address][self.cvx] += balance

        return None

    def query_balances(self) -> BalancesType:
        balances: BalancesType = defaultdict(lambda: defaultdict(Balance))
        gauges_to_token: dict[ChecksumEvmAddress, EvmToken] = {}

        # query addresses and gauges where they interacted
        addresses_with_deposits = self.addresses_with_deposits(
            product=EvmProduct.GAUGE,
            deposit_events={(HistoryEventType.DEPOSIT, HistoryEventSubType.NONE)},
        )

        # get details to query balances on chain
        chunk_size, call_order = get_chunk_size_call_order(self.evm_inquirer)
        for address, events in addresses_with_deposits.items():
            balances[address] = defaultdict(Balance)
            # Create a mapping of gauge to its token
            for event in events:
                if event.address is None:
                    continue
                if event.extra_data is None or (gauge_address := event.extra_data.get('gauge_address')) is None:  # noqa: E501
                    continue
                gauges_to_token[gauge_address] = event.asset.resolve_to_evm_token()

            balances[address] = query_gauges_balances(
                user_address=address,
                gauges_to_token=gauges_to_token,
                call_order=call_order,
                chunk_size=chunk_size,
                balances_contract=self._get_staking_contract_balances,
            )

        # query CVX locked but not staked
        cvx_lock_contract = self.evm_inquirer.contracts.contract(string_to_evm_address('0xCF50b810E57Ac33B91dCF525C6ddd9881B139332'))  # noqa: E501
        self._query_staked_cvx(balances, cvx_lock_contract)
        # query CVX staked
        cvx_lock_contract = self.evm_inquirer.contracts.contract(string_to_evm_address('0x72a19342e8F1838460eBFCCEf09F6585e32db86E'))  # noqa: E501
        self._query_staked_cvx(balances, cvx_lock_contract)

        return balances
