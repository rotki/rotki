from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.velodrome.balances import VelodromeLikeBalances
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_AERODROME

if TYPE_CHECKING:
    from rotkehlchen.chain.base.decoding.decoder import BaseTransactionDecoder
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer


class AerodromeBalances(VelodromeLikeBalances):
    def __init__(
            self,
            evm_inquirer: 'BaseInquirer',
            tx_decoder: 'BaseTransactionDecoder',
    ):
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            counterparty=CPT_AERODROME,
        )
