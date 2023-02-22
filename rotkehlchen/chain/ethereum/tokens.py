from typing import TYPE_CHECKING

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.makerdao.cache import ilk_cache_foreach
from rotkehlchen.chain.evm.tokens import EvmTokens
from rotkehlchen.chain.evm.types import asset_id_is_evm_token, string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_WETH
from rotkehlchen.globaldb.handler import GlobalDBHandler
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

    def __init__(
            self,
            database: 'DBHandler',
            ethereum_inquirer: 'EthereumInquirer',
    ) -> None:
        super().__init__(
            database=database,
            evm_inquirer=ethereum_inquirer,
        )
        self.tokens_for_proxies_set = set()
        self.tokens_for_proxies_set.add(A_DAI.resolve_to_evm_token())
        self.tokens_for_proxies_set.add(A_WETH.resolve_to_evm_token())  # WETH is also used
        # Add aave tokens
        self.tokens_for_proxies_set |= set(GlobalDBHandler().get_evm_tokens(
            chain_id=ChainID.ETHEREUM,
            protocol='aave',
        ))
        self.tokens_for_proxies_set |= set(GlobalDBHandler().get_evm_tokens(
            chain_id=ChainID.ETHEREUM,
            protocol='aave-v2',
        ))

    # -- methods that need to be implemented per chain
    def _get_token_exceptions(self) -> list[ChecksumEvmAddress]:
        exceptions = ETH_TOKEN_EXCEPTIONS.copy()
        with self.db.conn.read_ctx() as cursor:
            ignored_asset_ids = self.db.get_ignored_asset_ids(cursor=cursor)

        # TODO: Shouldn't this query be filtered in the DB?
        for asset_id in ignored_asset_ids:  # don't query for the ignored tokens
            if (evm_details := asset_id_is_evm_token(asset_id)) is not None and evm_details[0] == ChainID.ETHEREUM:  # noqa: E501
                exceptions.append(evm_details[1])

        return exceptions

    def maybe_detect_proxies_tokens(self, addresses: list[ChecksumEvmAddress]) -> None:
        """Detect tokens for proxies that are owned by the given addresses"""
        # Add Makerdao vault collateral tokens
        with GlobalDBHandler().conn.read_ctx() as cursor:
            ilk_collaterals = {x for _, _, x, _ in ilk_cache_foreach(cursor) if x != A_ETH}

        # We ignore A_ETH so all other ones should be tokens
        tokens_for_proxies: list[EvmToken] = list(self.tokens_for_proxies_set | ilk_collaterals)  # type: ignore[operator]  # noqa: E501
        proxies_mapping = self.evm_inquirer.proxies_inquirer.get_accounts_having_proxy()
        proxies_to_use = {k: v for k, v in proxies_mapping.items() if k in addresses}
        self._detect_tokens(
            addresses=list(proxies_to_use.values()),
            tokens_to_check=tokens_for_proxies,
        )
