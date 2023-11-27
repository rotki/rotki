import logging
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.interfaces.balances import ProtocolWithGauges
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.chain.evm.contracts import EvmContract
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_CVX
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

from .constants import CPT_CONVEX, CVX_LOCKER_V2, CVX_REWARDS

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.interfaces.balances import BalancesType
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.history.events.structures.evm_event import EvmEvent
    from rotkehlchen.types import CHAIN_IDS_WITH_BALANCE_PROTOCOLS

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class ConvexBalances(ProtocolWithGauges):
    """Query staked balances in the Convex gauges"""

    def __init__(
            self,
            database: DBHandler,
            evm_inquirer: 'EvmNodeInquirer',
            chain_id: 'CHAIN_IDS_WITH_BALANCE_PROTOCOLS',
    ):
        super().__init__(
            database=database,
            evm_inquirer=evm_inquirer,
            chain_id=chain_id,
            counterparty=CPT_CONVEX,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
            gauge_deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},  # noqa: E501
        )
        self.cvx = A_CVX.resolve_to_evm_token()

    def get_gauge_address(self, event: 'EvmEvent') -> ChecksumEvmAddress | None:
        if event.extra_data is None:
            return None
        return event.extra_data.get('gauge_address')  # can be None

    def _query_staked_cvx(
            self,
            balances: 'BalancesType',
            staking_contract: EvmContract,
            addresses_with_stake: list[ChecksumEvmAddress],
    ) -> None:
        """
        Query staking balances for CVX if there was a deposit event in Convex.
        The logic is the same for locked cvx and staked cvx that is why staking_contract
        is variable.
        The balances variable is mutated in this function.
        """
        cvx_price = Inquirer().find_usd_price(self.cvx)
        try:
            call_output = self.evm_inquirer.multicall(
                calls=[(
                    staking_contract.address,
                    staking_contract.encode(method_name='balanceOf', arguments=[address]),
                ) for address in addresses_with_stake],
            )
        except RemoteError as e:
            log.error(f'Failed to query convex balances due to {e!s}')
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

    def query_balances(self) -> 'BalancesType':
        balances = super().query_balances()  # Query the gauges
        addresses_with_stake_mapping = self.addresses_with_deposits(
            products=[EvmProduct.STAKING],
        )
        # addresses_with_deposits returns a mapping of address to evm event but since we will call
        # the staking contracts with the addresses as arguments we need the list of addresses to
        # index them later
        addresses_with_stake = list(addresses_with_stake_mapping.keys())
        if len(addresses_with_stake) == 0:
            return balances

        for contract_address in (CVX_REWARDS, CVX_LOCKER_V2):
            self._query_staked_cvx(
                balances=balances,
                staking_contract=self.evm_inquirer.contracts.contract(contract_address),
                addresses_with_stake=addresses_with_stake,
            )

        return balances
