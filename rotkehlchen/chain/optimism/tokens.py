from typing import TYPE_CHECKING

from rotkehlchen.chain.evm.tokens import EvmTokens
from rotkehlchen.chain.evm.types import asset_id_is_evm_token
from rotkehlchen.constants.assets import A_OPTIMISM_ETH
from rotkehlchen.types import ChainID, ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import OptimismInquirer


class OptimismTokens(EvmTokens):

    def __init__(self, database: 'DBHandler', optimism_inquirer: 'OptimismInquirer') -> None:
        super().__init__(database=database, evm_inquirer=optimism_inquirer)

    # -- methods that need to be implemented per chain
    def _get_token_exceptions(self) -> list[ChecksumEvmAddress]:
        exceptions = [A_OPTIMISM_ETH.resolve_to_evm_token().evm_address]
        with self.db.conn.read_ctx() as cursor:
            ignored_asset_ids = self.db.get_ignored_asset_ids(cursor=cursor)

        # TODO: Shouldn't this query be filtered in the DB?
        for asset_id in ignored_asset_ids:  # don't query for the ignored tokens
            if (evm_details := asset_id_is_evm_token(asset_id)) is not None and evm_details[0] == ChainID.OPTIMISM:  # noqa: E501
                exceptions.append(evm_details[1])

        return exceptions
