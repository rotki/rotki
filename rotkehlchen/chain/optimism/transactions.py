import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.optimism_superchain.transactions import OptimismSuperchainTransactions
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class OptimismTransactions(OptimismSuperchainTransactions):

    def __init__(
            self,
            optimism_inquirer: 'OptimismInquirer',
            database: 'DBHandler',
    ) -> None:
        super().__init__(node_inquirer=optimism_inquirer, database=database)
