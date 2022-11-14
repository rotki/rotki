import logging
from abc import ABCMeta, abstractmethod
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List, Optional, Sequence, Tuple

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.types import WeightedNode, string_to_evm_address
from rotkehlchen.chain.ethereum.utils import token_normalized_value
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, Price, SupportedBlockchain, Timestamp
from rotkehlchen.utils.misc import combine_dicts, get_chunks

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.gevent import DBCursor

    from .node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

TokenBalancesType = Tuple[
    Dict[ChecksumEvmAddress, Dict[EvmToken, FVal]],
    Dict[EvmToken, Price],
]

DetectedTokensType = Dict[
    ChecksumEvmAddress,
    Tuple[Optional[List[EvmToken]], Optional[Timestamp]],
]

# 08/08/2020
# Etherscan has by far the fastest responding server if you use a (free) API key
# The chunk length for Etherscan is limited though to 120 addresses due to the URI length.
# For all other nodes (mycrypto, avado cloud, blockscout) we have run some benchmarks
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


OTHER_MAX_TOKEN_CHUNK_LENGTH = 590

# maximum 32-bytes arguments in one call to a contract (either tokensBalance or multicall)
ETHERSCAN_MAX_ARGUMENTS_TO_CONTRACT = 122

# this is a number of arguments that a pure tokensBalance contract occupies when is added
# to multicall. In total, it occupies (7 + number of tokens passed) arguments.
PURE_TOKENS_BALANCE_ARGUMENTS = 7


def generate_multicall_chunks(
        chunk_length: int,
        addresses_to_tokens: Dict[ChecksumEvmAddress, List[EvmToken]],
) -> List[List[Tuple[ChecksumEvmAddress, List[EvmToken]]]]:
    """Generate appropriate num of chunks for multicall address->tokens, address->tokens query"""
    multicall_chunks = []
    free_space = chunk_length
    new_chunk = []
    for address, tokens in addresses_to_tokens.items():
        while len(tokens) > 0:
            free_space -= PURE_TOKENS_BALANCE_ARGUMENTS
            if free_space > len(tokens):
                new_chunk.append((address, tokens))
                free_space -= len(tokens)
                tokens = []
            else:
                if free_space > 0:
                    new_chunk.append((address, tokens[:free_space]))
                    tokens = tokens[free_space:]
                multicall_chunks.append(new_chunk)
                new_chunk = []  # start new chunk
                free_space = chunk_length
    if new_chunk != []:
        multicall_chunks.append(new_chunk)
    return multicall_chunks


class EvmTokens(metaclass=ABCMeta):
    def __init__(self, database: 'DBHandler', evm_inquirer: 'EvmNodeInquirer'):
        self.db = database
        self.evm_inquirer = evm_inquirer

    def _get_token_balances(
            self,
            address: ChecksumEvmAddress,
            tokens: List[EvmToken],
            call_order: Optional[Sequence[WeightedNode]],
    ) -> Dict[EvmToken, FVal]:
        """Queries the balances of multiple tokens for an address

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        - BadFunctionCallOutput if a local node is used and the contract for the
          token has no code. That means the chain is not synced
        """
        log.debug(
            f'Querying {self.evm_inquirer.chain_name} for multi token address balances',
            address=address,
            tokens_num=len(tokens),
        )
        result = self.evm_inquirer.contract_scan.call(
            node_inquirer=self.evm_inquirer,
            method_name='tokensBalance',
            arguments=[address, [x.evm_address for x in tokens]],
            call_order=call_order,
        )
        balances: Dict[EvmToken, FVal] = defaultdict(FVal)
        for token_balance, token in zip(result, tokens):
            if token_balance == 0:
                continue

            normalized_balance = token_normalized_value(token_balance, token)
            log.debug(
                f'Found {self.evm_inquirer.chain_name} {token.symbol}({token.evm_address}) '
                f'token balance for {address} and balance {normalized_balance}',
            )
            balances[token] += normalized_balance
        return balances

    def _get_multicall_token_balances(
            self,
            chunk: List[Tuple[ChecksumEvmAddress, List[EvmToken]]],
            call_order: Optional[Sequence['WeightedNode']] = None,
    ) -> Dict[ChecksumEvmAddress, Dict[EvmToken, FVal]]:
        """Gets token balances from a chunk of address -> token address

        May raise:
        - RemoteError if no result is queried in multicall
        """
        calls: List[Tuple[ChecksumEvmAddress, str]] = []
        for address, tokens in chunk:
            tokens_addrs = [token.evm_address for token in tokens]
            calls.append(
                (
                    self.node_inquirer.contract_scan.address,
                    self.node_inquirer.contract_scan.encode(
                        method_name='tokensBalance',
                        arguments=[address, tokens_addrs],
                    ),
                ),
            )
        results = self.node_inquirer.multicall(
            calls=calls,
            call_order=call_order,
        )
        balances: Dict[ChecksumEvmAddress, Dict[EvmToken, FVal]] = defaultdict(lambda: defaultdict(FVal))  # noqa: E501
        for (address, tokens), result in zip(chunk, results):
            decoded_result = self.node_inquirer.contract_scan.decode(  # pylint: disable=unsubscriptable-object  # noqa: E501
                result=result,
                method_name='tokensBalance',
                arguments=[address, [token.evm_address for token in tokens]],
            )[0]
            for token, token_balance in zip(tokens, decoded_result):
                if token_balance == 0:
                    continue

                normalized_balance = token_normalized_value(token_balance, token)
                log.debug(
                    f'Found {self.evm_inquirer.chain_name} {token.symbol}({token.evm_address}) '
                    f'token balance for {address} and balance {normalized_balance}',
                )
                balances[address][token] += normalized_balance
        return balances

    def _query_chunks(
            self,
            address: ChecksumEvmAddress,
            tokens: List[EvmToken],
            chunk_size: int,
            call_order: List[WeightedNode],
    ) -> Dict[EvmToken, FVal]:
        total_token_balances: Dict[EvmToken, FVal] = defaultdict(FVal)
        chunks = get_chunks(tokens, n=chunk_size)
        for chunk in chunks:
            new_token_balances = self._get_token_balances(
                address=address,
                tokens=chunk,
                call_order=call_order,
            )
            total_token_balances = combine_dicts(total_token_balances, new_token_balances)
        return total_token_balances

    def detect_tokens(
            self,
            only_cache: bool,
            addresses: List[ChecksumEvmAddress],
    ) -> DetectedTokensType:
        """
        Detect tokens for the given addresses.

        If only_cache is True, only tokens saved in the database are returned.
        Otherwise, tokens are re-detected.

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        - BadFunctionCallOutput if a local node is used and the contract for the
          token has no code. That means the chain is not synced
        """
        if only_cache is False:
            self._detect_tokens(addresses=addresses)
            addresses_info: DetectedTokensType = {}
            with self.db.conn.read_ctx() as cursor:
                for address in addresses:
                    addresses_info[address] = self.db.get_tokens_for_address(
                        cursor=cursor,
                        address=address,
                        blockchain=self.evm_inquirer.blockchain,
                    )

        return addresses_info

    def _detect_tokens(self, addresses: List[ChecksumEvmAddress]) -> None:
        """
        Detect tokens for the given addresses.

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        - BadFunctionCallOutput if a local node is used and the contract for the
          token has no code. That means the chain is not synced
        """
        all_tokens = GlobalDBHandler().get_evm_tokens(
            chain_id=self.evm_inquirer.chain_id,
            exceptions=self._get_token_exceptions(),
            except_protocols=['balancer'],
        )

        if self.evm_inquirer.connected_to_any_web3():
            chunk_size = OTHER_MAX_TOKEN_CHUNK_LENGTH
            # skipping etherscan because chunk size is too big for etherscan
            call_order = self.evm_inquirer.default_call_order(skip_etherscan=True)
        else:
            chunk_size = ETHERSCAN_MAX_ARGUMENTS_TO_CONTRACT
            call_order = [self.evm_inquirer.etherscan_node]
        for address in addresses:
            token_balances = self._query_chunks(
                address=address,
                tokens=all_tokens,
                chunk_size=chunk_size,
                call_order=call_order,
            )
            detected_tokens = list(token_balances.keys())
            with self.db.user_write() as write_cursor:
                self.db.save_tokens_for_address(
                    write_cursor=write_cursor,
                    address=address,
                    blockchain=self.evm_inquirer.blockchain,
                    tokens=detected_tokens,
                )

    def query_tokens_for_addresses(
            self,
            addresses: List[ChecksumEvmAddress],
    ) -> TokenBalancesType:
        """Queries token balances for a list of addresses
        Returns the token balances of each address and the usd prices of the tokens.

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        - BadFunctionCallOutput if a local node is used and the contract for the
          token has no code. That means the chain is not synced
        """
        addresses_to_balances: Dict[ChecksumEvmAddress, Dict[EvmToken, FVal]] = {}
        all_tokens = set()
        addresses_to_tokens: Dict[ChecksumEvmAddress, List[EvmToken]] = {}

        if self.evm_inquirer.connected_to_any_web3():
            chunk_size = OTHER_MAX_TOKEN_CHUNK_LENGTH
            # skipping etherscan because chunk size is too big for etherscan
            call_order = self.evm_inquirer.default_call_order(skip_etherscan=True)
        else:
            chunk_size = ETHERSCAN_MAX_ARGUMENTS_TO_CONTRACT
            call_order = [self.evm_inquirer.etherscan_node]

        with self.db.conn.read_ctx() as cursor:
            for address in addresses:
                saved_list, _ = self.db.get_tokens_for_address(cursor, address=address, blockchain=SupportedBlockchain.ETHEREUM)  # noqa: E501
                if saved_list is None:
                    continue  # Do not query if we know the address has no tokens
                all_tokens.update(saved_list)
                addresses_to_tokens[address] = saved_list

        multicall_chunks = generate_multicall_chunks(
            addresses_to_tokens=addresses_to_tokens,
            chunk_length=chunk_size,
        )
        for chunk in multicall_chunks:
            addresses_to_balances.update(self._get_multicall_token_balances(
                chunk=chunk,
                call_order=call_order,
            ))

        token_usd_price: Dict[EvmToken, Price] = {}
        for token in all_tokens:
            token_usd_price[token] = Inquirer.find_usd_price(asset=token)

        return addresses_to_balances, token_usd_price

    # -- methods to be implemented by child classes
    @abstractmethod
    def _get_token_exceptions(self) -> List[EvmToken]:
        """
        Returns a list of token addresses that will not be taken into account
        when performing token detection.

        Each chain needs to implement any chain-specific exceptions here.
        """
        ...
