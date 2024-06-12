from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.gearbox.balances import GearboxCommonBalances
from rotkehlchen.chain.optimism.modules.gearbox.constants import (
    GEAR_IDENTIFIER_OPT,
    GEAR_STAKING_CONTRACT,
)

if TYPE_CHECKING:
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.db.dbhandler import DBHandler


class GearboxBalances(GearboxCommonBalances):
    def __init__(self, database: 'DBHandler', evm_inquirer: 'OptimismInquirer') -> None:
        super().__init__(
            database=database,
            evm_inquirer=evm_inquirer,
            staking_contract=GEAR_STAKING_CONTRACT,
            native_token_id=GEAR_IDENTIFIER_OPT,
        )
