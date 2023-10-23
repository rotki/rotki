import logging
from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.chain.ethereum.interfaces.balances import ProtocolWithBalance
from rotkehlchen.chain.ethereum.utils import asset_normalized_value
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_GLM
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter

from .constants import CPT_OCTANT, OCTANT_DEPOSITS

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.interfaces.balances import BalancesType
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import CHAIN_IDS_WITH_BALANCE_PROTOCOLS

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OctantBalances(ProtocolWithBalance):
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
            counterparty=CPT_OCTANT,
            deposit_event_types={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
        )
        self.glm = A_GLM.resolve_to_evm_token()

    def query_balances(self) -> 'BalancesType':
        """Query balances of locked GLM in Octant"""
        balances: BalancesType = defaultdict(lambda: defaultdict(Balance))

        # fetch deposit events
        addresses_with_deposits = list(self.addresses_with_deposits(products=None))

        deposits_contract = self.evm_inquirer.contracts.contract(OCTANT_DEPOSITS)
        try:
            call_output = self.evm_inquirer.multicall(
                calls=[(
                    deposits_contract.address,
                    deposits_contract.encode(method_name='deposits', arguments=[address]),
                ) for address in addresses_with_deposits],
            )
        except RemoteError as e:
            log.error(f'Failed to query octant locked balances due to {e!s}')
            return balances

        glm_price = Inquirer().find_usd_price(self.glm)
        for idx, result in enumerate(call_output):
            address = addresses_with_deposits[idx]
            amount_raw = deposits_contract.decode(result, 'deposits', arguments=[address])[0]
            amount = asset_normalized_value(amount_raw, self.glm)
            if amount == ZERO:
                continue

            balance = Balance(amount=amount, usd_value=glm_price * amount)
            balances[address][self.glm] += balance

        return balances
