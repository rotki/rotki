import logging
from collections import defaultdict
from typing import Dict, List, Tuple

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.assets.resolver import AssetResolver
from rotkehlchen.chain.ethereum.manager import EthereumManager
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.constants.ethereum import ETH_SCAN
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ChecksumEthAddress, EthTokenInfo, Price
from rotkehlchen.utils.misc import get_chunks

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

TokensReturn = Tuple[
    Dict[ChecksumEthAddress, Dict[EthereumToken, FVal]],
    Dict[EthereumToken, Price],
]


class EthTokens():

    def __init__(self, database: DBHandler, ethereum: EthereumManager):
        self.db = database
        self.ethereum = ethereum

    def detect_tokens_for_addresses(self, addresses: List[ChecksumEthAddress]) -> TokensReturn:
        token_usd_price = {}
        all_tokens = AssetResolver().get_all_eth_token_info()
        # With etherscan with chunks > 120, we get request uri too large
        # so the limitation is not in the gas, but in the request uri length
        chunks = list(get_chunks(all_tokens, n=120))

        result = {}
        for address in addresses:
            balances: Dict[EthereumToken, FVal] = defaultdict(FVal)
            for chunk in chunks:
                ret = self._get_multitoken_account_balance(tokens=chunk, account=address)
                for token_identifier, value in ret.items():
                    token = EthereumToken(token_identifier)
                    balances[token] += value
                    if token in token_usd_price:
                        continue
                    # else get the price
                    try:
                        usd_price = Inquirer().find_usd_price(token)
                    except RemoteError:
                        usd_price = Price(ZERO)
                    token_usd_price[token] = usd_price

            result[address] = balances

        return result, token_usd_price

    def query_tokens_for_addresses(self, addresses: List[ChecksumEthAddress]) -> TokensReturn:
        return self.detect_tokens_for_addresses(addresses)

    def _get_multitoken_multiaccount_balance(
            self,
            tokens: List[EthTokenInfo],
            accounts: List[ChecksumEthAddress],
    ) -> Dict[str, Dict[ChecksumEthAddress, FVal]]:
        """Queries a list of accounts for balances of multiple tokens

        Return a dictionary with keys being tokens and value a dictionary of
        account to balances

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        - BadFunctionCallOutput if a local node is used and the contract for the
          token has no code. That means the chain is not synced
        """
        log.debug(
            'Querying ethereum chain for multi token multi account balances',
            eth_addresses=accounts,
            tokens_num=len(tokens),
        )
        balances: Dict[str, Dict[ChecksumEthAddress, FVal]] = defaultdict(dict)
        result = self.ethereum.call_contract(
            contract_address=ETH_SCAN.address,
            abi=ETH_SCAN.abi,
            method_name='tokensBalances',
            arguments=[accounts, [x.address for x in tokens]],
        )
        for acc_idx, account in enumerate(accounts):
            for tk_idx, token in enumerate(tokens):
                token_amount = result[acc_idx][tk_idx]
                if token_amount != 0:
                    balances[token.identifier][account] = token_normalized_value(
                        token_amount, token.decimals,
                    )
        return balances

    def _get_multitoken_account_balance(
            self,
            tokens: List[EthTokenInfo],
            account: ChecksumEthAddress,
    ) -> Dict[str, FVal]:
        """Queries balances of multiple tokens for an account

        Return a dictionary with keys being tokens and value a dictionary of
        account to balances

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        - BadFunctionCallOutput if a local node is used and the contract for the
          token has no code. That means the chain is not synced
        """
        log.debug(
            'Querying ethereum chain for multi token account balances',
            eth_address=account,
            tokens_num=len(tokens),
        )
        balances: Dict[str, FVal] = {}
        result = self.ethereum.call_contract(
            contract_address=ETH_SCAN.address,
            abi=ETH_SCAN.abi,
            method_name='tokensBalance',
            arguments=[account, [x.address for x in tokens]],
        )
        for tk_idx, token in enumerate(tokens):
            token_amount = result[tk_idx]
            if token_amount != 0:
                balances[token.identifier] = token_normalized_value(token_amount, token.decimals)
        return balances
