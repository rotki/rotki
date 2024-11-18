from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.balancer.balances import BalancerCommonBalances
from rotkehlchen.chain.evm.decoding.balancer.constants import CPT_BALANCER_V2
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress


class Balancerv2Balances(BalancerCommonBalances):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_BALANCER_V2,
        )

    def get_active_pool_tokens(self) -> set['ChecksumEvmAddress']:
        addresses_with_activities = self.addresses_with_activity(event_types={
            (HistoryEventType.RECEIVE, HistoryEventSubType.RECEIVE_WRAPPED),
        })
        active_pools: set[ChecksumEvmAddress] = set()
        for events in addresses_with_activities.values():
            active_pools.update(event.asset.resolve_to_evm_token().evm_address for event in events)

        return active_pools
