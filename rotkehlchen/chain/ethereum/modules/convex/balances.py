from collections import defaultdict
from typing import TYPE_CHECKING

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmProduct
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.interfaces.balances import ProtocolWithBalance
from rotkehlchen.chain.ethereum.modules.curve.balances import query_gauges_balances
from rotkehlchen.chain.evm.tokens import get_chunk_size_call_order
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.types import ChecksumEvmAddress

from .constants import CPT_CONVEX

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer


class ConvexBalances(ProtocolWithBalance):
    """Query staked balances in the Convex gauges"""

    def __init__(self, database: DBHandler, evm_inquirer: 'EvmNodeInquirer'):
        super().__init__(database=database, evm_inquirer=evm_inquirer, counterparty=CPT_CONVEX)

    def query_balances(self) -> dict[ChecksumEvmAddress, dict[EvmToken, Balance]]:
        balances: dict[ChecksumEvmAddress, dict[EvmToken, Balance]] = {}
        gauges_to_token: dict[ChecksumEvmAddress, EvmToken] = {}

        # query addresses and gauges where they interacted
        addresses_with_deposits = self.addresses_with_deposits(
            product=EvmProduct.CONVEX_GAUGE,
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

        return balances
