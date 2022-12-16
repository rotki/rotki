from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.tokens import EvmTokens
from rotkehlchen.types import ChainID, ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import OptimismInquirer


class OptimismTokens(EvmTokens):

    def __init__(self, database: 'DBHandler', optimism_inquirer: 'OptimismInquirer') -> None:
        super().__init__(database=database, evm_inquirer=optimism_inquirer)

    # -- methods that need to be implemented per chain
    def _get_token_exceptions(self) -> list[ChecksumEvmAddress]:
        exceptions = []
        with self.db.conn.read_ctx() as cursor:
            ignored_assets = self.db.get_ignored_assets(cursor=cursor)

        # TODO: Shouldn't this query be filtered in the DB?
        for asset in ignored_assets:  # don't query for the ignored tokens
            if asset.is_evm_token() and asset.resolve_to_evm_token().chain_id == ChainID.OPTIMISM:
                exceptions.append(EvmToken(asset.identifier).evm_address)

        return exceptions
