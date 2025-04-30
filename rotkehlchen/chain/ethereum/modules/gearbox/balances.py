from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.modules.gearbox.constants import (
    GEAR_STAKING_CONTRACT,
    GEAR_TOKEN,
)
from rotkehlchen.chain.evm.decoding.gearbox.balances import GearboxCommonBalances

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.decoding.decoder import EthereumTransactionDecoder
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


class GearboxBalances(GearboxCommonBalances):
    def __init__(
            self,
            evm_inquirer: 'EthereumInquirer',
            tx_decoder: 'EthereumTransactionDecoder',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            staking_contract=GEAR_STAKING_CONTRACT,
            gear_token=GEAR_TOKEN,
        )
