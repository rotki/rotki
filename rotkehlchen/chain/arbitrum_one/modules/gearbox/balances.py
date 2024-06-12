from typing import TYPE_CHECKING


from rotkehlchen.chain.arbitrum_one.modules.gearbox.constants import (
    GEAR_IDENTIFIER_ARB,
    GEAR_STAKING_CONTRACT,
)
from rotkehlchen.chain.evm.decoding.gearbox.balances import GearboxCommonBalances

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.db.dbhandler import DBHandler


class GearboxBalances(GearboxCommonBalances):
    def __init__(self, database: 'DBHandler', evm_inquirer: 'ArbitrumOneInquirer') -> None:
        super().__init__(
            database=database,
            evm_inquirer=evm_inquirer,
            staking_contract=GEAR_STAKING_CONTRACT,
            native_token_id=GEAR_IDENTIFIER_ARB,
        )
