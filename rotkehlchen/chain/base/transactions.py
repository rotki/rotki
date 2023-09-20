import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.optimism_superchain.transactions import OptimismSuperchainTransactions
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BaseTransactions(OptimismSuperchainTransactions):

    def __init__(
            self,
            base_inquirer: 'BaseInquirer',
            database: 'DBHandler',
    ) -> None:
        super().__init__(node_inquirer=base_inquirer, database=database)
