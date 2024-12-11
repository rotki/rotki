from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.tokens import EvmTokens
from rotkehlchen.chain.gnosis.modules.giveth.constants import (
    GIVPOW_ADDRESS,
    GNOSIS_GIVPOWERSTAKING_WRAPPER,
)
from rotkehlchen.chain.gnosis.modules.monerium.constants import GNOSIS_MONERIUM_LEGACY_ADDRESSES

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.types import ChecksumEvmAddress

    from .node_inquirer import GnosisInquirer


class GnosisTokens(EvmTokens):

    def __init__(self, database: 'DBHandler', gnosis_inquirer: 'GnosisInquirer') -> None:
        super().__init__(database=database, evm_inquirer=gnosis_inquirer)

    # -- methods that need to be implemented per chain
    def _per_chain_token_exceptions(self) -> set['ChecksumEvmAddress']:
        return GNOSIS_MONERIUM_LEGACY_ADDRESSES | {
            GIVPOW_ADDRESS, GNOSIS_GIVPOWERSTAKING_WRAPPER,
        }
