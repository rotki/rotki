import logging
import random
from collections import defaultdict
from typing import Dict, List, Optional, Sequence, Tuple

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.manager import EthereumManager, NodeName
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.constants.ethereum import ETH_SCAN
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.errors import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ChecksumEthAddress, Price
from rotkehlchen.utils.misc import get_chunks, ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

TokensReturn = Tuple[
    Dict[ChecksumEthAddress, Dict[EthereumToken, FVal]],
    Dict[EthereumToken, Price],
]

# 08/08/2020
# Etherscan has by far the fastest responding server if you use a (free) API key
# The chunk length for Etherscan is limited though to 120 addresses due to the URI length.
# For all other nodes (mycrypto, avado cloud, blockscout) we have ran some benchmarks
# with them being queried randomly with different chunk lenghts. They are all for an account with:
# - 29 ethereum addresses
# - rotki knows of 1010 different ethereum tokens as of this writing
# Type        |  Chunk Length | Elapsed Seconds | Avg. secs per call
# Open Nodes  |     300       |      105        |      2.379
# Open Nodes  |     400       |      112        |      2.735
# Open Nodes  |     450       |       90        |      2.287
# Open Nodes  |     520       |       89        |      2.275
# Open Nodes  |     575       |       75        |      1.982
# Open Nodes  |     585       |       77        |      2.034
# Open Nodes  |     590       |       74        |      1.931
# Open Nodes  |     590       |       79        |      2.086
# Open Nodes  |     600       |       80        |      2.068
# Open Nodes  |     600       |       86        |      2.275
#
# Etherscan   |     120       |       112       |      2.218
# Etherscan   |     120       |       99        |      1.957
# Etherscan   |     120       |       102       |      2.026
#
# With this we have settled on a 590 chunk length. When we surpass 1180 ethereum
# tokens the benchmark will probably have to run again.


ETHERSCAN_MAX_TOKEN_CHUNK_LENGTH = 120
OTHER_MAX_TOKEN_CHUNK_LENGTH = 590


class EthTokens():

    def __init__(self, database: DBHandler, ethereum: EthereumManager):
        self.db = database
        self.ethereum = ethereum

    def detect_tokens_for_address(
            self,
            address: ChecksumEthAddress,
            token_usd_price: Dict[EthereumToken, Price],
            etherscan_chunks: List[List[EthereumToken]],
            other_chunks: List[List[EthereumToken]],
    ) -> Dict[EthereumToken, FVal]:
        balances: Dict[EthereumToken, FVal] = defaultdict(FVal)
        if self.ethereum.connected_to_any_web3():
            call_order = []
            if NodeName.OWN in self.ethereum.web3_mapping:
                call_order = [NodeName.OWN]
            for chunk in other_chunks:
                self._get_tokens_balance_and_price(
                    address=address,
                    tokens=chunk,
                    balances=balances,
                    token_usd_price=token_usd_price,
                    call_order=call_order + random.sample(
                        (NodeName.MYCRYPTO, NodeName.BLOCKSCOUT, NodeName.AVADO_POOL),
                        3,
                    ),
                )
        else:
            for chunk in etherscan_chunks:
                self._get_tokens_balance_and_price(
                    address=address,
                    tokens=chunk,
                    balances=balances,
                    token_usd_price=token_usd_price,
                    call_order=(NodeName.ETHERSCAN,),
                )

        # now that detection happened we also have to save it in the DB for the address
        self.db.save_tokens_for_address(address, list(balances.keys()))

        return balances

    def query_tokens_for_addresses(
            self,
            addresses: List[ChecksumEthAddress],
            force_detection: bool,
    ) -> TokensReturn:
        """Queries/detects token balances for a list of addresses

        If an address's tokens were recently autodetected they are not detected again but the
        balances are simply queried. Unless force_detection is True.

        Returns the token balances of each address and the usd prices of the tokens
        """
        log.debug(
            'Querying/detecting token balances for all addresses',
            force_detection=force_detection,
        )
        ignored_assets = self.db.get_ignored_assets()
        exceptions = [
            # Ignore the veCRV balance in token query. It's already detected by
            # defi SDK as part of locked CRV in Vote Escrowed CRV. Which is the right way
            # to approach it as there is no way to assign a price to 1 veCRV. It
            # can be 1 CRV locked for 4 years or 4 CRV locked for 1 year etc.
            string_to_ethereum_address('0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2'),
        ]
        for asset in ignored_assets:  # don't query for the ignored tokens
            if asset.is_eth_token():  # type ignore since we know asset is a token
                exceptions.append(EthereumToken.from_asset(asset).ethereum_address)  # type: ignore
        all_tokens = GlobalDBHandler().get_ethereum_tokens(exceptions=exceptions)
        # With etherscan with chunks > 120, we get request uri too large
        # so the limitation is not in the gas, but in the request uri length
        etherscan_chunks = list(get_chunks(all_tokens, n=ETHERSCAN_MAX_TOKEN_CHUNK_LENGTH))
        other_chunks = list(get_chunks(all_tokens, n=OTHER_MAX_TOKEN_CHUNK_LENGTH))
        now = ts_now()
        token_usd_price: Dict[EthereumToken, Price] = {}
        result = {}

        for address in addresses:
            saved_list = self.db.get_tokens_for_address_if_time(address=address, current_time=now)
            if force_detection or saved_list is None:
                balances = self.detect_tokens_for_address(
                    address=address,
                    token_usd_price=token_usd_price,
                    etherscan_chunks=etherscan_chunks,
                    other_chunks=other_chunks,
                )
            else:
                if len(saved_list) == 0:
                    continue  # Do not query if we know the address has no tokens

                balances = defaultdict(FVal)
                self._get_tokens_balance_and_price(
                    address=address,
                    tokens=saved_list,
                    balances=balances,
                    token_usd_price=token_usd_price,
                    call_order=None,  # use defaults
                )

            result[address] = balances

        return result, token_usd_price

    def _get_tokens_balance_and_price(
            self,
            address: ChecksumEthAddress,
            tokens: List[EthereumToken],
            balances: Dict[EthereumToken, FVal],
            token_usd_price: Dict[EthereumToken, Price],
            call_order: Optional[Sequence[NodeName]],
    ) -> None:
        ret = self._get_multitoken_account_balance(
            tokens=tokens,
            account=address,
            call_order=call_order,
        )
        for token_identifier, value in ret.items():
            token = EthereumToken.from_identifier(token_identifier)
            if token is None:  # should not happen
                log.warning(
                    f'Could not initialize token with identifier {token_identifier}. '
                    f'Should not happen. Skipping its token balance query',
                )
                continue
            balances[token] += value
            if token in token_usd_price:
                continue
            # else get the price
            try:
                usd_price = Inquirer().find_usd_price(token)
            except RemoteError:
                usd_price = Price(ZERO)
            token_usd_price[token] = usd_price

    def _get_multitoken_account_balance(
            self,
            tokens: List[EthereumToken],
            account: ChecksumEthAddress,
            call_order: Optional[Sequence[NodeName]],
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
        result = ETH_SCAN.call(
            ethereum=self.ethereum,
            method_name='tokensBalance',
            arguments=[account, [x.ethereum_address for x in tokens]],
            call_order=call_order,
        )
        for tk_idx, token in enumerate(tokens):
            token_amount = result[tk_idx]
            if token_amount != 0:
                normalized_amount = token_normalized_value(token_amount, token)
                log.debug(
                    f'Found {token.symbol}({token.ethereum_address}) token balance for '
                    f'{account} and amount {normalized_amount}',
                )
                balances[token.identifier] = normalized_amount
        return balances
