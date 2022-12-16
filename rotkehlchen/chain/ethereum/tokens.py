from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.evm.tokens import EvmTokens
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import EthereumInquirer

ETH_TOKEN_EXCEPTIONS = [
    # Ignore the veCRV balance in token query. It's already detected by
    # defi SDK as part of locked CRV in Vote Escrowed CRV. Which is the right way
    # to approach it as there is no way to assign a price to 1 veCRV. It
    # can be 1 CRV locked for 4 years or 4 CRV locked for 1 year etc.
    string_to_evm_address('0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2'),
    # Ignore for now xsushi since is queried by defi SDK. We'll do it for now
    # since the SDK entry might return other tokens from sushi and we don't
    # fully support sushi now.
    string_to_evm_address('0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272'),
    # Ignore stkAave since it's queried by defi SDK.
    string_to_evm_address('0x4da27a545c0c5B758a6BA100e3a049001de870f5'),
    # Ignore the following tokens. They are old tokens of upgraded contracts which
    # duplicated the balances at upgrade instead of doing a token swap.
    # e.g.: https://github.com/rotki/rotki/issues/3548
    # TODO: At some point we should actually remove them from the DB and
    # upgrade possible occurences in the user DB
    #
    # Old contract of Fetch.ai
    string_to_evm_address('0x1D287CC25dAD7cCaF76a26bc660c5F7C8E2a05BD'),
]


class EthereumTokens(EvmTokens):

    def __init__(self, database: 'DBHandler', ethereum_inquirer: 'EthereumInquirer') -> None:
        super().__init__(database=database, evm_inquirer=ethereum_inquirer)

    # -- methods that need to be implemented per chain
    def _get_token_exceptions(self) -> list[ChecksumEvmAddress]:
        exceptions = ETH_TOKEN_EXCEPTIONS.copy()
        with self.db.conn.read_ctx() as cursor:
            ignored_assets = self.db.get_ignored_assets(cursor=cursor)

        # TODO: Shouldn't this query be filtered in the DB?
        for asset in ignored_assets:  # don't query for the ignored tokens
            if asset.is_evm_token() and asset.resolve_to_evm_token().chain_id == ChainID.ETHEREUM:
                exceptions.append(EvmToken(asset.identifier).evm_address)

        return exceptions
