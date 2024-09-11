from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.velodrome.balances import VelodromeLikeBalances
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_VELODROME

if TYPE_CHECKING:
    from rotkehlchen.chain.optimism.decoding.decoder import OptimismTransactionDecoder
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer


class VelodromeBalances(VelodromeLikeBalances):
    def __init__(
            self,
            evm_inquirer: 'OptimismInquirer',
            tx_decoder: 'OptimismTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_VELODROME,
        )
