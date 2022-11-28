import logging
from abc import ABCMeta
from typing import TYPE_CHECKING, Optional

from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:

    from .decoding.decoder import EVMTransactionDecoder
    from .node_inquirer import EvmNodeInquirer
    from .tokens import EvmTokens
    from .transactions import EvmTransactions

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class EvmManager(metaclass=ABCMeta):
    """EvmManager defines a basic implementation for EVM chains."""
    def __init__(
            self,
            node_inquirer: 'EvmNodeInquirer',
            transactions: 'EvmTransactions',
            tokens: 'EvmTokens',
            transactions_decoder: 'EVMTransactionDecoder',
    ) -> None:
        super().__init__()
        self.node_inquirer = node_inquirer
        self.transactions = transactions
        self.tokens = tokens
        self.transactions_decoder = transactions_decoder

    def get_historical_balance(
            self,
            address: ChecksumEvmAddress,
            block_number: int,
    ) -> Optional[FVal]:
        """Attempts to get a historical eth balance from the local own node only.
        If there is no node or the node can't query historical balance (not archive) then
        returns None"""
        return self.node_inquirer.get_historical_balance(address, block_number)
