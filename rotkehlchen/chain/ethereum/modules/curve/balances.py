from collections import defaultdict
from typing import TYPE_CHECKING, Callable

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.accounting.structures.evm_event import EvmProduct
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.interfaces.balances import ProtocolWithBalance
from rotkehlchen.chain.evm.tokens import get_chunk_size_call_order
from rotkehlchen.chain.evm.types import WeightedNode
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import get_chunks

from .constants import CPT_CURVE

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer


def query_gauges_balances(
        user_address: ChecksumEvmAddress,
        gauges_to_token: dict[ChecksumEvmAddress, EvmToken],
        call_order: list[WeightedNode],
        chunk_size: int,
        balances_contract: Callable,
) -> dict[EvmToken, Balance]:
    """
    Query the set of gauges in gauges_to_token and return the balances for each
    lp token desposited in all gauges.
    """
    balances: dict[EvmToken, Balance] = defaultdict(Balance)
    gauge_chunks = get_chunks(list(gauges_to_token.keys()), n=chunk_size)
    for gauge_chunk in gauge_chunks:
        tokens = [gauges_to_token[staking_addr] for staking_addr in gauge_chunk]
        gauges_balances = balances_contract(
            address=user_address,
            staking_addresses=gauge_chunk,
            tokens=tokens,
            call_order=call_order,
        )

        # Now map the gauge to the underlying token
        for lp_token, balance in gauges_balances.items():
            lp_token_price = Inquirer().find_usd_price(lp_token)
            balances[lp_token] += Balance(
                amount=balance,
                usd_value=lp_token_price * balance,
            )

    return balances


class CurveBalances(ProtocolWithBalance):
    """
    Query balances in Curve gauges.
    LP tokens are already queried by the normal token detection.
    """

    def __init__(self, database: DBHandler, evm_inquirer: 'EvmNodeInquirer'):
        super().__init__(database=database, evm_inquirer=evm_inquirer, counterparty=CPT_CURVE)

    def query_balances(self) -> dict[ChecksumEvmAddress, dict[EvmToken, Balance]]:
        balances: dict[ChecksumEvmAddress, dict[EvmToken, Balance]] = {}
        gauges_to_token: dict[ChecksumEvmAddress, EvmToken] = {}

        # query addresses and gauges where they interacted
        addresses_with_deposits = self.addresses_with_deposits(
            product=EvmProduct.GAUGE,
            deposit_events={(HistoryEventType.DEPOSIT, HistoryEventSubType.DEPOSIT_ASSET)},
        )

        # get details to query balances on chain
        chunk_size, call_order = get_chunk_size_call_order(self.evm_inquirer)
        for address, events in addresses_with_deposits.items():
            balances[address] = defaultdict(Balance)
            # Create a mapping of a gauge to its token
            for event in events:
                if event.address is None:
                    continue
                gauges_to_token[event.address] = event.asset.resolve_to_evm_token()

            balances[address] = query_gauges_balances(
                user_address=address,
                gauges_to_token=gauges_to_token,
                call_order=call_order,
                chunk_size=chunk_size,
                balances_contract=self._get_staking_contract_balances,
            )

        return balances
