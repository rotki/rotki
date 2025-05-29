from collections.abc import Sequence
from typing import TYPE_CHECKING

from rotkehlchen.chain.ethereum.modules.curve.constants import VOTING_ESCROW
from rotkehlchen.chain.ethereum.modules.makerdao.cache import ilk_cache_foreach
from rotkehlchen.chain.ethereum.modules.monerium.constants import (
    ETHEREUM_MONERIUM_LEGACY_ADDRESSES,
)
from rotkehlchen.chain.evm.tokens import EvmTokensWithDSProxy
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.structures import EvmTokenDetectionData
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
    # upgrade possible occurrences in the user DB
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
            token_exceptions=None,
        )
        dai = A_DAI.resolve_to_evm_token()
        weth = A_WETH.resolve_to_evm_token()
        self.tokens_for_proxies = [
            EvmTokenDetectionData(
                identifier=dai.identifier,
                address=dai.evm_address,
                decimals=dai.decimals,  # type: ignore  # TODO: those tokens have decimals. We need to fix the type in the EVMToken class.
            ), EvmTokenDetectionData(
                identifier=weth.identifier,
                address=weth.evm_address,
                decimals=weth.decimals,  # type: ignore
            ),
        ]
        # Add aave tokens
        aave_tokens, _ = GlobalDBHandler.get_token_detection_data(
            chain_id=ChainID.ETHEREUM,
            exceptions=set(),
            protocol='aave',
        )
        self.tokens_for_proxies.extend(aave_tokens)
        aave_v2_tokens, _ = GlobalDBHandler.get_token_detection_data(
            chain_id=ChainID.ETHEREUM,
            exceptions=set(),
            protocol='aave-v2',
        )
        self.tokens_for_proxies.extend(aave_v2_tokens)

        # Add Makerdao vault collateral tokens
        with GlobalDBHandler().conn.read_ctx() as cursor:
            for _, _, asset, _ in ilk_cache_foreach(cursor):
                if asset == A_ETH:
                    continue

                token = asset.resolve_to_evm_token()
                self.tokens_for_proxies.append(EvmTokenDetectionData(
                    identifier=token.identifier,
                    address=token.evm_address,
                    decimals=token.decimals,  # type: ignore
                ))

    # -- methods that need to be implemented per chain
    def _per_chain_token_exceptions(self) -> set[ChecksumEvmAddress]:
        return ETH_TOKEN_EXCEPTIONS.copy() | ETHEREUM_MONERIUM_LEGACY_ADDRESSES

    def maybe_detect_proxies_tokens(self, addresses: Sequence[ChecksumEvmAddress]) -> None:
        """Detect tokens for proxies that are owned by the given addresses"""
        # We ignore A_ETH so all other ones should be tokens
        proxies_mapping = self.evm_inquirer.proxies_inquirer.get_accounts_having_proxy()
        proxies_to_use = {k: v for k, v in proxies_mapping.items() if k in addresses}
        detected_tokens = self._detect_tokens(
            addresses=list(proxies_to_use.values()),
            tokens_to_check=self.tokens_for_proxies,
        )
        with self.db.user_write() as write_cursor:
            for addr, tokens in detected_tokens.items():
                self.db.save_tokens_for_address(
                    write_cursor=write_cursor,
                    address=addr,
                    tokens=tokens,
                    blockchain=self.evm_inquirer.blockchain,
                )
