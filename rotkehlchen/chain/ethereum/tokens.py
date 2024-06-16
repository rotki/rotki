from collections.abc import Sequence
from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.modules.curve.constants import VOTING_ESCROW
from rotkehlchen.chain.ethereum.modules.makerdao.cache import ilk_cache_foreach
from rotkehlchen.chain.evm.tokens import EvmTokensWithDSProxy
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_WETH
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.types import ChainID, ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import EthereumInquirer

ETH_TOKEN_EXCEPTIONS = {
    # Ignore the veCRV balance in token query. It's already detected by
    # defi SDK as part of locked CRV in Vote Escrowed CRV. Which is the right way
    # to approach it as there is no way to assign a price to 1 veCRV. It
    # can be 1 CRV locked for 4 years or 4 CRV locked for 1 year etc.
    VOTING_ESCROW,
    # Ignore for now xsushi since is queried by defi SDK. We'll do it for now
    # since the SDK entry might return other tokens from sushi and we don't
    # fully support sushi now.
    string_to_evm_address('0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272'),
    # Ignore the following tokens. They are old tokens of upgraded contracts which
    # duplicated the balances at upgrade instead of doing a token swap.
    # e.g.: https://github.com/rotki/rotki/issues/3548
    # TODO: At some point we should actually remove them from the DB and
    # upgrade possible occurences in the user DB
    #
    # Old contract of Fetch.ai
    string_to_evm_address('0x1D287CC25dAD7cCaF76a26bc660c5F7C8E2a05BD'),
}


class EthereumTokens(EvmTokensWithDSProxy):

    def __init__(
            self,
            database: 'DBHandler',
            ethereum_inquirer: 'EthereumInquirer',
    ) -> None:
        """
        TODO:
        Think if limiting to specific tokens makes sense for proxies. Can miss balances.
        Also this keeps all tokens in this list in memory in perpetuity. This is not a good idea.
        """
        super().__init__(
            database=database,
            evm_inquirer=ethereum_inquirer,
        )
        self.tokens_for_proxies = [A_DAI.resolve_to_evm_token(), A_WETH.resolve_to_evm_token()]
        # Add aave tokens
        self.tokens_for_proxies.extend(GlobalDBHandler().get_evm_tokens(
            chain_id=ChainID.ETHEREUM,
            protocol='aave',
        ))
        self.tokens_for_proxies.extend(GlobalDBHandler().get_evm_tokens(
            chain_id=ChainID.ETHEREUM,
            protocol='aave-v2',
        ))
        # Add Makerdao vault collateral tokens
        with GlobalDBHandler().conn.read_ctx() as cursor:
            self.tokens_for_proxies.extend([x for _, _, x, _ in ilk_cache_foreach(cursor) if x != A_ETH])  # type: ignore  # noqa: E501

    # -- methods that need to be implemented per chain
    def _per_chain_token_exceptions(self) -> set[ChecksumEvmAddress]:
        return ETH_TOKEN_EXCEPTIONS.copy()

    def maybe_detect_proxies_tokens(self, addresses: Sequence[ChecksumEvmAddress]) -> None:
        """Detect tokens for proxies that are owned by the given addresses"""
        # We ignore A_ETH so all other ones should be tokens
        proxies_mapping = self.evm_inquirer.proxies_inquirer.get_accounts_having_proxy()
        proxies_to_use = {k: v for k, v in proxies_mapping.items() if k in addresses}
        self._detect_tokens(
            addresses=list(proxies_to_use.values()),
            tokens_to_check=self.tokens_for_proxies,
        )
