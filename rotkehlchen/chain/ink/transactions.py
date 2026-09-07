import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.l2_with_l1_fees.transactions import L2WithL1FeesTransactions
from rotkehlchen.logging import RotkehlchenLogsAdapter

if TYPE_CHECKING:
    from rotkehlchen.chain.ink.node_inquirer import InkInquirer
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class InkTransactions(L2WithL1FeesTransactions):

    def __init__(
            self,
            ink_inquirer: InkInquirer,
            database: DBHandler,
    ) -> None:
        super().__init__(node_inquirer=ink_inquirer, database=database)
