import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Sequence, Tuple

from rotkehlchen.assets.asset import EthereumToken
from rotkehlchen.chain.ethereum.constants import ETHERSCAN_NODE
from rotkehlchen.chain.ethereum.manager import EthereumManager
from rotkehlchen.chain.ethereum.types import WeightedNode, string_to_ethereum_address
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.constants.ethereum import ETH_SCAN
from rotkehlchen.db.dbhandler import DBHandler
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChecksumEthAddress, Price, Timestamp
from rotkehlchen.utils.misc import combine_dicts, get_chunks

if TYPE_CHECKING:
    from rotkehlchen.chain.drivers.gevent import DBCursor

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

TokenBalancesType = Tuple[
    Dict[ChecksumEthAddress, Dict[EthereumToken, FVal]],
    Dict[EthereumToken, Price],
]

DetectedTokensType = Dict[
    ChecksumEthAddress,
    Tuple[Optional[List[EthereumToken]], Optional[Timestamp]],
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

    def _get_token_balances(
            self,
            account: ChecksumEthAddress,
            tokens: List[EthereumToken],
            call_order: Optional[Sequence[WeightedNode]],
    ) -> Dict[EthereumToken, FVal]:
        """Queries the balances of multiple tokens for an account

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
        result = ETH_SCAN.call(
            ethereum=self.ethereum,
            method_name='tokensBalance',
            arguments=[account, [x.ethereum_address for x in tokens]],
            call_order=call_order,
        )
        balances: Dict[EthereumToken, FVal] = defaultdict(FVal)
        for token_balance, token in zip(result, tokens):
            if token_balance == 0:
                continue

            normalized_balance = token_normalized_value(token_balance, token)
            log.debug(
                f'Found {token.symbol}({token.ethereum_address}) token balance for '
                f'{account} and balance {normalized_balance}',
            )
            balances[token] += normalized_balance
        return balances

    def _query_chunks(
            self,
            account: ChecksumEthAddress,
            chunks: Iterable[List[EthereumToken]],
            querying_etherscan: bool,
    ) -> Dict[EthereumToken, FVal]:
        total_token_balances: Dict[EthereumToken, FVal] = defaultdict(FVal)
        for chunk in chunks:
            if querying_etherscan is True:
                call_order = [ETHERSCAN_NODE]
            else:
                call_order = self.ethereum.default_call_order()
            new_token_balances = self._get_token_balances(
                account=account,
                tokens=chunk,
                call_order=call_order,
            )
            total_token_balances = combine_dicts(total_token_balances, new_token_balances)
        return total_token_balances

    def detect_tokens(
            self,
            only_cache: bool,
            accounts: List[ChecksumEthAddress],
    ) -> DetectedTokensType:
        """
        Detect tokens for the given accounts.

        If only_cache is True, only tokens saved in the database are returned.
        Otherwise, tokens are re-detected.

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        - BadFunctionCallOutput if a local node is used and the contract for the
          token has no code. That means the chain is not synced
        """
        with self.db.conn.read_ctx() as cursor:
            if only_cache is False:
                self._detect_tokens(cursor, accounts=accounts)

            accounts_info: DetectedTokensType = {}
            for account in accounts:
                accounts_info[account] = self.db.get_tokens_for_address(
                    cursor=cursor,
                    address=account,
                )

        return accounts_info

    def _detect_tokens(
            self,
            cursor: 'DBCursor',
            accounts: List[ChecksumEthAddress],
    ) -> None:
        """
        Detect tokens for the given accounts.

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        - BadFunctionCallOutput if a local node is used and the contract for the
          token has no code. That means the chain is not synced
        """
        exceptions = [
            # Ignore the veCRV balance in token query. It's already detected by
            # defi SDK as part of locked CRV in Vote Escrowed CRV. Which is the right way
            # to approach it as there is no way to assign a price to 1 veCRV. It
            # can be 1 CRV locked for 4 years or 4 CRV locked for 1 year etc.
            string_to_ethereum_address('0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2'),
            # Ignore for now xsushi since is queried by defi SDK. We'll do it for now
            # since the SDK entry might return other tokens from sushi and we don't
            # fully support sushi now.
            string_to_ethereum_address('0x8798249c2E607446EfB7Ad49eC89dD1865Ff4272'),
            # Ignore stkAave since it's queried by defi SDK.
            string_to_ethereum_address('0x4da27a545c0c5B758a6BA100e3a049001de870f5'),
            # Ignore the following tokens. They are old tokens of upgraded contracts which
            # duplicated the balances at upgrade instead of doing a token swap.
            # e.g.: https://github.com/rotki/rotki/issues/3548
            # TODO: At some point we should actually remove them from the DB and
            # upgrade possible occurences in the user DB
            #
            # Old contract of Fetch.ai
            string_to_ethereum_address('0x1D287CC25dAD7cCaF76a26bc660c5F7C8E2a05BD'),
        ]
        ignored_assets = self.db.get_ignored_assets(cursor=cursor)
        for asset in ignored_assets:  # don't query for the ignored tokens
            if asset.is_eth_token():  # type ignore since we know asset is a token
                exceptions.append(EthereumToken.from_asset(asset).ethereum_address)  # type: ignore
        all_tokens = GlobalDBHandler().get_ethereum_tokens(
            exceptions=exceptions,
            except_protocols=['balancer'],
        )
        for account in accounts:
            if self.ethereum.connected_to_any_web3():
                querying_etherscan = False
                tokens_batch_size = OTHER_MAX_TOKEN_CHUNK_LENGTH
            else:
                querying_etherscan = True
                tokens_batch_size = ETHERSCAN_MAX_TOKEN_CHUNK_LENGTH
            token_balances = self._query_chunks(
                account=account,
                chunks=get_chunks(all_tokens, n=tokens_batch_size),
                querying_etherscan=querying_etherscan,
            )
            detected_tokens = list(token_balances.keys())
            with self.db.user_write() as write_cursor:
                self.db.save_tokens_for_address(write_cursor, account, detected_tokens)

    def query_tokens_for_addresses(
            self,
            addresses: List[ChecksumEthAddress],
    ) -> TokenBalancesType:
        """Queries token balances for a list of addresses
        Returns the token balances of each address and the usd prices of the tokens.

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        - BadFunctionCallOutput if a local node is used and the contract for the
          token has no code. That means the chain is not synced
        """
        address_to_balance: Dict[ChecksumEthAddress, Dict[EthereumToken, FVal]] = {}
        all_tokens = set()

        with self.db.conn.read_ctx() as cursor:
            for address in addresses:
                saved_list, _ = self.db.get_tokens_for_address(cursor, address=address)
                if saved_list is None:
                    continue  # Do not query if we know the address has no tokens
                all_tokens.update(saved_list)

                token_balances = self._get_token_balances(
                    account=address,
                    tokens=saved_list,
                    call_order=None,  # use defaults
                )
                address_to_balance[address] = token_balances

        token_usd_price: Dict[EthereumToken, Price] = {}
        for token in all_tokens:
            token_usd_price[token] = Inquirer.find_usd_price(asset=token)

        return address_to_balance, token_usd_price
