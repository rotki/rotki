from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.modules.thegraph.constants import CONTRACT_STAKING
from rotkehlchen.chain.evm.decoding.thegraph.balances import ThegraphCommonBalances
from rotkehlchen.constants.assets import A_GRT

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.db.dbhandler import DBHandler


class ThegraphBalances(ThegraphCommonBalances):

    def __init__(
            self,
            database: 'DBHandler',
            evm_inquirer: 'EthereumInquirer',
    ) -> None:
        super().__init__(
            database=database,
            evm_inquirer=evm_inquirer,
            native_asset=A_GRT,
            staking_contract=CONTRACT_STAKING,
        )
