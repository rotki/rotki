from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.decoding.velodrome.balances import VelodromeLikeBalances
from rotkehlchen.chain.evm.decoding.velodrome.constants import CPT_AERODROME
from rotkehlchen.db.dbhandler import DBHandler

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer


class AerodromeBalances(VelodromeLikeBalances):
    def __init__(
            self,
            database: DBHandler,
            evm_inquirer: 'BaseInquirer',
    ):
        super().__init__(
            database=database,
            evm_inquirer=evm_inquirer,
            counterparty=CPT_AERODROME,
        )
