from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.velodrome.balances import VelodromeLikeBalances
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_AERODROME

from .constants import A_AERO, VOTING_ESCROW_CONTRACT_ADDRESS

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
            voting_escrow_address=VOTING_ESCROW_CONTRACT_ADDRESS,
            protocol_token=A_AERO.resolve_to_evm_token(),
        )
