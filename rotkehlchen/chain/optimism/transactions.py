import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.transactions import EvmTransactions
from rotkehlchen.db.optimismtx import DBOptimismTx
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import OptimismInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OptimismTransactions(EvmTransactions):

    def __init__(
            self,
            optimism_inquirer: 'OptimismInquirer',
            database: 'DBHandler',
    ) -> None:
        super().__init__(evm_inquirer=optimism_inquirer, database=database)
        self.dbevmtx = DBOptimismTx(database)
