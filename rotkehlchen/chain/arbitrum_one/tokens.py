from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.tokens import EvmTokens

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import ArbitrumOneInquirer


class ArbitrumOneTokens(EvmTokens):

    def __init__(self, database: 'DBHandler', arbitrum_one_inquirer: 'ArbitrumOneInquirer') -> None:  # noqa: E501
        super().__init__(database=database, evm_inquirer=arbitrum_one_inquirer)
