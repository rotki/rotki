from typing import TYPE_CHECKING


from rotkehlchen.chain.ethereum.modules.gearbox.constants import (
    GEAR_IDENTIFIER,
    GEAR_STAKING_CONTRACT,
)
from rotkehlchen.chain.evm.decoding.gearbox.balances import GearboxCommonBalances

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler


class GearboxBalances(GearboxCommonBalances):
    def __init__(self, database: 'DBHandler', evm_inquirer: 'EthereumInquirer') -> None:
        super().__init__(
            database=database,
            evm_inquirer=evm_inquirer,
            staking_contract=GEAR_STAKING_CONTRACT,
            native_token_id=GEAR_IDENTIFIER,
        )
