from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.velodrome.balances import VelodromeLikeBalances
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_VELODROME
from rotkehlchen.db.dbhandler import DBHandler

if TYPE_CHECKING:
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.types import CHAIN_IDS_WITH_BALANCE_PROTOCOLS


class VelodromeBalances(VelodromeLikeBalances):
    def __init__(
            self,
            database: DBHandler,
            evm_inquirer: 'OptimismInquirer',
            chain_id: 'CHAIN_IDS_WITH_BALANCE_PROTOCOLS',
    ):
        super().__init__(
            database=database,
            evm_inquirer=evm_inquirer,
            chain_id=chain_id,
            counterparty=CPT_VELODROME,
        )
