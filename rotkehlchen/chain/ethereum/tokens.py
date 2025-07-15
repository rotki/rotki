from collections.abc import Sequence

from rotkehlchen.chain.ethereum.modules.curve.constants import VOTING_ESCROW
from rotkehlchen.chain.ethereum.modules.monerium.constants import (
    ETHEREUM_MONERIUM_LEGACY_ADDRESSES,
)
from rotkehlchen.chain.evm.proxies_inquirer import ProxyType
from rotkehlchen.chain.evm.tokens import EvmTokensWithProxies
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChecksumEvmAddress

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


class EthereumTokens(EvmTokensWithProxies):

    # -- methods that need to be implemented per chain
    def _per_chain_token_exceptions(self) -> set[ChecksumEvmAddress]:
        return ETH_TOKEN_EXCEPTIONS.copy() | ETHEREUM_MONERIUM_LEGACY_ADDRESSES

    def maybe_detect_proxies_tokens(self, addresses: Sequence[ChecksumEvmAddress]) -> None:
        """Detect tokens for proxies that are owned by the given addresses"""
        # We ignore A_ETH so all other ones should be tokens
        proxies_mapping = self.evm_inquirer.proxies_inquirer.get_accounts_having_proxy()
        proxy_addresses = set()
        for proxy_type in ProxyType:
            proxy_addresses |= {v for k, v in proxies_mapping[proxy_type].items() if k in addresses}  # noqa: E501

        if len(proxy_addresses) == 0:
            return

        # Call EvmToken's _query_new_tokens to avoid calling maybe_detect_proxies_tokens again.
        super(EvmTokensWithProxies, self)._query_new_tokens(addresses=list(proxy_addresses))
