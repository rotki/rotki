from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.gearbox.balances import GearboxCommonBalances
from rotkehlchen.chain.optimism.modules.gearbox.constants import (
    GEAR_STAKING_CONTRACT,
    GEAR_TOKEN_OPT,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.optimism.decoding.decoder import OptimismTransactionDecoder
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer


class GearboxBalances(GearboxCommonBalances):
    def __init__(
            self,
            evm_inquirer: 'OptimismInquirer',
            tx_decoder: 'OptimismTransactionDecoder',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            staking_contract=GEAR_STAKING_CONTRACT,
            gear_token=GEAR_TOKEN_OPT,
        )
