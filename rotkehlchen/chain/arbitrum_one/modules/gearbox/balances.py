from typing import TYPE_CHECKING

from rotkehlchen.chain.arbitrum_one.modules.gearbox.constants import (
    GEAR_STAKING_CONTRACT,
    GEAR_TOKEN_ARB,
)
from rotkehlchen.chain.evm.decoding.gearbox.balances import GearboxCommonBalances

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.decoding.decoder import ArbitrumOneTransactionDecoder
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer


class GearboxBalances(GearboxCommonBalances):
    def __init__(
            self,
            evm_inquirer: 'ArbitrumOneInquirer',
            tx_decoder: 'ArbitrumOneTransactionDecoder',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            tx_decoder=tx_decoder,
            staking_contract=GEAR_STAKING_CONTRACT,
            gear_token=GEAR_TOKEN_ARB,
        )
