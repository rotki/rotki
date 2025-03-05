from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.decoding.velodrome.balances import VelodromeLikeBalances
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_VELODROME

from .constants import VOTING_ESCROW_CONTRACT_ADDRESS

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
            voting_escrow_address=VOTING_ESCROW_CONTRACT_ADDRESS,
            protocol_token=Asset('eip155:10/erc20:0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db').resolve_to_evm_token(),
        )
