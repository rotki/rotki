from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.balancer.balances import BalancerCommonBalances
from rotkehlchen.chain.evm.decoding.balancer.constants import CPT_BALANCER_V1

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.decoder import EVMTransactionDecoder
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirer
    from rotkehlchen.types import ChecksumEvmAddress


class Balancerv1Balances(BalancerCommonBalances):
    def __init__(
            self,
            evm_inquirer: 'EvmNodeInquirer',
            tx_decoder: 'EVMTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_BALANCER_V1,
        )

    def get_active_pool_tokens(self) -> set['ChecksumEvmAddress']:
        from rotkehlchen.globaldb.handler import GlobalDBHandler
        return set(GlobalDBHandler.get_addresses_by_protocol(
            protocol=CPT_BALANCER_V1,
            chain_id=self.evm_inquirer.chain_id,
        ))
