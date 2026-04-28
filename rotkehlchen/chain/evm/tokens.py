import logging
from abc import ABC
from collections import defaultdict, deque
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeVar, cast

from rotkehlchen.assets.asset import Asset, EvmToken, Nft
from rotkehlchen.assets.utils import (
    token_normalized_value,
    token_normalized_value_decimals,
)
from rotkehlchen.balances.historical import HistoricalBalancesManager
from rotkehlchen.chain.evm.proxies_inquirer import ProxyType
from rotkehlchen.chain.evm.types import WeightedNode, asset_id_is_evm_token
from rotkehlchen.chain.structures import EvmTokenDetectionData
from rotkehlchen.constants import ONE, ZERO
from rotkehlchen.constants.resolver import tokenid_to_collectible_id
from rotkehlchen.errors.misc import NotFoundError, RemoteError, RequestTooLargeError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_evm_address
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Price,
    SupportedBlockchain,
    Timestamp,
    TokenKind,
)
from rotkehlchen.utils.misc import combine_dicts, get_chunks

from .constants import ETHERSCAN_MAX_ARGUMENTS_TO_CONTRACT, ZERO_ADDRESS
from .contracts import EvmContract

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirerWithProxies
    from rotkehlchen.db.dbhandler import DBHandler

    from .node_inquirer import EvmNodeInquirer

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

TokenBalancesType = tuple[
    dict[ChecksumEvmAddress, dict[EvmToken, FVal]],
    dict[EvmToken, Price],
]

DetectedTokensType = dict[
    ChecksumEvmAddress,
    tuple[list[EvmToken] | None, Timestamp | None],
]
DetectedTokenBalanceAsset = Asset | EvmToken
DetectedTokenBalancesType = dict[ChecksumEvmAddress, dict[DetectedTokenBalanceAsset, FVal]]


@dataclass
class TokenChunkQueryResult:
    """Result of querying token balances for one address across chunked requests.

    Attributes:
    - balances: accumulated detected balances across successful chunk queries.
    - had_failures: True when at least one chunk could not be queried even after
      retry/split/indexer fallback handling. In that case results are considered
      unreliable for cache persistence.
    """
    balances: dict[DetectedTokenBalanceAsset, FVal]
    had_failures: bool

# 27/11/2024
# Etherscan has by far the fastest responding server if you use an API key
# The chunk length for Etherscan is limited though to 120 addresses due to the URI length.
# For all other nodes (ankr, cloudflare, flashbots) we have run some benchmarks
# with them being queried randomly with different chunk lengths.
# - They are for a single account
# - rotki knows of 5264 different ethereum tokens as of this writing
# - The code used is available in https://github.com/rotki/rotki/pull/8951
# chunk size, time, node, seed, comments
#
# 375, 5.452023983001709,  flashbots
# 375, 5.356801986694336,  flashbots , 42
# 375, 8.883646965026855,  cloudflare
# 375, 10.064039945602417, cloudflare
# 375, 6.45735502243042,   cloudflare
# 375, 5.277329921722412,  cloudflare, 80
# 375, 4.732897043228149,  ankr      , 90
# 500, 4.8045032024383545, ankr + flashbots, 90,  ankr and cloudlare had a single call out of gas
# 480, 5.05453896522522, ankr, 90, ankr had a single call out of gas. Cloudflare okey
# 460, 3.771683931350708, ankr + cloudflare, 90, only 1 request to ankr failed
# 460, 4.571718215942383, ankr + cloudflare, 90, only 1 request to ankr failed
# 460, 6.436861991882324, flashbots, 42
# 460, 3.726022243499756, flahbots + ankr, 80
# 460, 7.433700084686279, cloudflare + ankr, 460
#
# With this we have settled on a 460 chunk length since it was the highest round number that
# didn't hit any issue executing the query in the open nodes.


OTHER_MAX_TOKEN_CHUNK_LENGTH = 460

# this is a number of arguments that a pure tokensBalance contract occupies when is added
# to multicall. In total, it occupies (7 + number of tokens passed) arguments.
PURE_TOKENS_BALANCE_ARGUMENTS = 7

T = TypeVar('T')


def generate_multicall_chunks(
        chunk_length: int,
        addresses_to_tokens: Mapping[ChecksumEvmAddress, Sequence[T]],
) -> list[list[tuple[ChecksumEvmAddress, Sequence[T]]]]:
    """Generate appropriate num of chunks for multicall address->tokens, address->tokens query"""
    multicall_chunks = []
    free_space = chunk_length
    new_chunk = []
    for address, address_tokens in addresses_to_tokens.items():
        tokens = address_tokens
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


def get_rpc_first_chunk_size_call_order(
        evm_inquirer: 'EvmNodeInquirer',
        web3_node_chunk_size: int = OTHER_MAX_TOKEN_CHUNK_LENGTH,
) -> tuple[int, list[WeightedNode]]:
    """Return chunk size and RPC-first call order with indexer fallback.

    Behavior:
    - if any RPC node is connected, use RPC-only order with the web3 chunk size.
    - if no RPC node is connected but RPC nodes are configured, keep RPC nodes first and append
      the indexer as fallback, still using the web3 chunk size (lazy connect in `_query`).
    - if no RPC nodes are configured, use indexer-only order and inquirer indexer chunk size.
    """
    rpc_call_order = evm_inquirer.default_call_order(skip_indexers=True)
    if evm_inquirer.connected_to_any_node():
        return web3_node_chunk_size, rpc_call_order

    if len(rpc_call_order) == 0:
        return evm_inquirer.INDEXER_CHUNK_SIZE, [evm_inquirer.indexers_node]

    return web3_node_chunk_size, [*rpc_call_order, evm_inquirer.indexers_node]


class EvmTokens(ABC):  # noqa: B024
    INDEXER_CHUNK_SIZE = ETHERSCAN_MAX_ARGUMENTS_TO_CONTRACT

    def __init__(
            self,
            database: 'DBHandler',
            evm_inquirer: 'EvmNodeInquirer',
            token_exceptions: set[ChecksumEvmAddress] | None = None,
    ):
        self.db = database
        self.evm_inquirer = evm_inquirer
        self.token_exceptions = token_exceptions if token_exceptions is not None else set()
        self.INDEXER_CHUNK_SIZE = evm_inquirer.INDEXER_CHUNK_SIZE

    def get_token_balances(
            self,
            address: ChecksumEvmAddress,
            tokens: list[EvmTokenDetectionData],
            call_order: Sequence[WeightedNode] | None,
    ) -> dict[DetectedTokenBalanceAsset, FVal]:
        """Query multiple token balances for a wallet address.
        Returns Asset objects instead of EvmTokens for performance optimization since
        we avoid loading from the database extra information not used here.

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
        balances: dict[DetectedTokenBalanceAsset, FVal] = defaultdict(FVal)
        try:
            result = self.evm_inquirer.contract_scan.call(
                node_inquirer=self.evm_inquirer,
                method_name='tokens_balance',
                arguments=[address, [x.address for x in tokens]],
                call_order=call_order,
            )
        except RequestTooLargeError:
            # Let callers reduce chunk size and retry.
            raise
        except RemoteError as e:
            log.error(
                f'{self.evm_inquirer.chain_name} tokensBalance call failed for address {address}.'
                f' Token addresses: {[x.address for x in tokens]}. Error: {e}',
            )
            return balances

        try:
            for token_balance, token in zip(result, tokens, strict=True):
                if token_balance == 0:
                    continue

                normalized_balance = token_normalized_value_decimals(
                    token_amount=token_balance,
                    token_decimals=token.decimals,
                )
                log.debug(
                    f'Found {self.evm_inquirer.chain_name} {token.identifier} '
                    f'token balance for {address} and balance {normalized_balance}',
                )
                balances[EvmToken(token.identifier)] += normalized_balance
        except ValueError:
            log.error(
                f'{self.evm_inquirer.chain_name} tokensBalance returned different length '
                f'of results({len(result)}) to amount of tokens ({len(tokens)}).'
                f'{result=}.{tokens=}',
            )

        return balances

    def _get_multicall_token_balances(
            self,
            chunk: list[tuple[ChecksumEvmAddress, Sequence[EvmToken]]],
            call_order: Sequence['WeightedNode'] | None = None,
    ) -> dict[ChecksumEvmAddress, dict[EvmToken, FVal]]:
        """Gets token balances from a chunk of address -> token address

        May raise:
        - RemoteError if no result is queried in multicall
        """
        calls: list[tuple[ChecksumEvmAddress, str]] = []
        encode_arguments: list[list] = []
        for address, tokens in chunk:
            tokens_addrs = [token.evm_address for token in tokens]
            args = [address, tokens_addrs]
            encode_arguments.append(args)
            calls.append(
                (
                    self.evm_inquirer.contract_scan.address,
                    self.evm_inquirer.contract_scan.encode(
                        method_name='tokens_balance',
                        arguments=args,
                    ),
                ),
            )
        results = self.evm_inquirer.multicall(
            calls=calls,
            call_order=call_order,
        )
        balances: dict[ChecksumEvmAddress, dict[EvmToken, FVal]] = defaultdict(lambda: defaultdict(FVal))  # noqa: E501
        for (address, tokens), result, args in zip(chunk, results, encode_arguments, strict=True):
            decoded_result = self.evm_inquirer.contract_scan.decode(
                result=result,
                method_name='tokens_balance',
                arguments=args,
            )[0]
            for token, token_balance in zip(tokens, decoded_result, strict=True):
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
            tokens: list[EvmTokenDetectionData],
            chunk_size: int,
            call_order: list[WeightedNode],
    ) -> TokenChunkQueryResult:
        """Processes token balance queries in batches of chunk_size to avoid hitting gas limits.
        Uses Asset objects directly instead of EvmToken to minimize database queries.

        Starts with the given `call_order` and chunk size. If a chunk is too large, it retries
        smaller chunks first using the same call order (preserving RPC-first behavior). Once a
        chunk is at or below `INDEXER_CHUNK_SIZE`, request-size failures are retried with
        indexer-only calls chunked by `INDEXER_CHUNK_SIZE`.
        """
        total_token_balances: dict[DetectedTokenBalanceAsset, FVal] = defaultdict(FVal)
        had_failures = False
        chunks_to_process: deque[tuple[list[EvmTokenDetectionData], bool]] = deque(
            (chunk, False) for chunk in get_chunks(tokens, n=chunk_size)
        )
        while len(chunks_to_process) > 0:
            chunk, use_indexer_only = chunks_to_process.popleft()
            try:
                new_token_balances = self.get_token_balances(
                    address=address,
                    tokens=chunk,
                    call_order=[self.evm_inquirer.indexers_node] if use_indexer_only else call_order,  # noqa: E501
                )
            except RequestTooLargeError:
                if use_indexer_only is False and len(chunk) <= self.INDEXER_CHUNK_SIZE:
                    log.warning(
                        f'{self.evm_inquirer.chain_name} tokensBalance chunk too large '
                        f'for address {address}. Retrying with indexer-only calls in '
                        f'chunks of {self.INDEXER_CHUNK_SIZE}.',
                    )
                    indexer_chunks = list(get_chunks(chunk, n=self.INDEXER_CHUNK_SIZE))
                    for item in reversed(indexer_chunks):
                        chunks_to_process.appendleft((item, True))
                    continue

                if use_indexer_only is True and len(chunk) <= self.INDEXER_CHUNK_SIZE:
                    had_failures = True
                    log.error(
                        f'{self.evm_inquirer.chain_name} tokensBalance call failed '
                        f'for address {address} even with indexer-only chunk size '
                        f'{self.INDEXER_CHUNK_SIZE}.',
                    )
                    continue

                smaller_chunk_size = max(self.INDEXER_CHUNK_SIZE, len(chunk) // 2)
                log.warning(
                    f'{self.evm_inquirer.chain_name} tokensBalance chunk too large '
                    f'for address {address}. Retrying by splitting {len(chunk)} '
                    f'tokens into chunks of {smaller_chunk_size}.',
                )
                smaller_chunks = list(get_chunks(chunk, n=smaller_chunk_size))
                for item in reversed(smaller_chunks):
                    chunks_to_process.appendleft((item, use_indexer_only))
                continue

            total_token_balances = combine_dicts(total_token_balances, new_token_balances)

        return TokenChunkQueryResult(balances=total_token_balances, had_failures=had_failures)

    def _compute_detected_tokens_info(self, addresses: Sequence[ChecksumEvmAddress]) -> DetectedTokensType:  # noqa: E501
        """
        Generate a structure that contains information about the addresses that tokens
        were requested for.
        It generates a dictionary where key is an address and value is
        either a list of tokens or the timestamp of the last tokens query for that address.
        """
        addresses_info = {}
        with self.db.conn.read_ctx() as cursor:
            for address in addresses:
                addresses_info[address] = self.db.get_tokens_for_address(
                    cursor=cursor,
                    address=address,
                    blockchain=self.evm_inquirer.blockchain,
                    token_exceptions=self._per_chain_token_exceptions(),
                )

        return addresses_info

    def _query_new_tokens(self, addresses: Sequence[ChecksumEvmAddress]) -> None:
        """Run token detection and persist results for the given addresses.

        Cache-safety behavior:
        - ERC20 detection returns both detected tokens and addresses with failed detection.
        - Any address in the failed set is considered unreliable for this run and is not
          persisted to the token cache (even if partial tokens were detected).
        - ERC721 detection is executed only for addresses that did not fail ERC20 detection.

        This avoids destructive cache overwrites (e.g. replacing previously cached tokens with
        an empty/partial list after a failed detection query).
        """
        erc20_tokens, erc721_tokens = GlobalDBHandler.get_token_detection_data(
            chain_id=self.evm_inquirer.chain_id,
            exceptions=self._get_token_exceptions(),
        )
        detected_erc20_tokens, failed_detection_addresses, detected_erc20_balances = self._detect_tokens(  # noqa: E501
            addresses=addresses,
            tokens_to_check=erc20_tokens,
        )
        all_detected_tokens = self._detect_erc721_tokens(
            addresses=[
                address for address in addresses
                if address not in failed_detection_addresses
            ],
            tokens_to_check=erc721_tokens,
            detected_tokens=detected_erc20_tokens,
        )
        with self.db.user_write() as write_cursor:
            self.db.set_blockchain_detected_token_balances_cache(
                write_cursor=write_cursor,
                blockchain=self.evm_inquirer.blockchain,
                balances_per_address=detected_erc20_balances,
                failed_detection_addresses=failed_detection_addresses,
            )
            for address, detected_tokens in all_detected_tokens.items():
                if address in failed_detection_addresses:
                    log.warning(
                        f'{self.evm_inquirer.chain_name} token detection failed '
                        f'for address {address}. '
                        'Skipping cache update to avoid persisting incomplete token results.',
                    )
                    continue

                self.db.save_tokens_for_address(
                    write_cursor=write_cursor,
                    address=address,
                    blockchain=self.evm_inquirer.blockchain,
                    tokens=detected_tokens,
                )

    def _detect_erc721_tokens(
            self,
            addresses: Sequence[ChecksumEvmAddress],
            tokens_to_check: list[EvmTokenDetectionData],
            detected_tokens: dict[ChecksumEvmAddress, list[Asset]],
    ) -> dict[ChecksumEvmAddress, list[Asset]]:
        """Detect ERC-721 tokens owned by the given addresses based on historical events.
        For each address, checks token ownership from historical events and saves
        detected tokens to the database.

        May raise:
        - RemoteError if there is a problem with a query to an external service such as Etherscan.
        """
        if len(tokens_to_check) == 0:
            return detected_tokens

        historical_balance_manager = HistoricalBalancesManager(self.db)
        erc721_contract = EvmContract(
            address=ZERO_ADDRESS,
            abi=self.evm_inquirer.contracts.erc721_abi,
        )
        for address in addresses:
            try:
                token_balances = historical_balance_manager.get_erc721_tokens_balances(
                    assets=tuple(Asset(x.identifier) for x in tokens_to_check),
                    address=address,
                )
            except (NotFoundError, DeserializationError) as e:
                log.error(f'Failed to get erc721 token balances for {address} due to {e}. Skipping.')  # noqa: E501
                continue

            filtered_tokens, calls = [], []
            for token in token_balances:
                if (collectible_id := tokenid_to_collectible_id(token.identifier)) is not None:
                    calls.append((
                        token.evm_address,
                        erc721_contract.encode('ownerOf', arguments=[int(collectible_id)]),
                    ))
                    filtered_tokens.append(token)

            valid_tokens, outputs = [], self.evm_inquirer.multicall_2(calls=calls, require_success=False)  # noqa: E501
            for token, (status, result) in zip(filtered_tokens, outputs, strict=False):
                if status is False or len(result) == 0:  # multicall can return success but with empty data when contract call fails  # noqa: E501
                    log.error(f'Skipping token {token} for address {address} due to failed ownerOf call')  # noqa: E501
                    continue

                try:
                    if deserialize_evm_address(erc721_contract.decode(
                            result=result,
                            method_name='ownerOf',
                            arguments=[int(tokenid_to_collectible_id(token.identifier))],  # type: ignore[arg-type]  # will always be available
                    )[0]) != address:
                        log.debug(f'Address {address} no longer owns erc721 token {token}. Skipping...')  # noqa: E501
                        continue
                except DeserializationError as e:
                    log.error(f'Failed to deserialize owner address of erc721 token {token} due to {e!s}')  # noqa: E501
                    continue

                valid_tokens.append(token)

            detected_tokens[address].extend(valid_tokens)

        return detected_tokens

    def detect_tokens(
            self,
            only_cache: bool,
            addresses: Sequence[ChecksumEvmAddress],
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
            self._query_new_tokens(addresses)

        return self._compute_detected_tokens_info(addresses)

    def _get_token_detection_chunk_size_call_order(self) -> tuple[int, list[WeightedNode]]:
        """Return chunk size and call order used by token detection queries.

        We always start with RPC nodes. If there is no connected node yet, we still build
        an RPC-first order (lazy connect in `_query`) and append indexers only as a final
        fallback.
        """
        return get_rpc_first_chunk_size_call_order(
            evm_inquirer=self.evm_inquirer,
            web3_node_chunk_size=OTHER_MAX_TOKEN_CHUNK_LENGTH,
        )

    def _detect_tokens(
            self,
            addresses: Sequence[ChecksumEvmAddress],
            tokens_to_check: list[EvmTokenDetectionData],
    ) -> tuple[
        dict[ChecksumEvmAddress, list[Asset]],
        set[ChecksumEvmAddress],
        DetectedTokenBalancesType,
    ]:
        """Detect ERC20 tokens per address and track unreliable detection runs.

        Returns:
        - detected_tokens: address -> detected token list for successful detection runs.
        - failed_addresses: addresses where token querying had failures (see
          ``TokenChunkQueryResult.had_failures``).
        - detected_balances: address -> detected token balances for successful runs.

        For failed addresses, this method intentionally does not return partial token results,
        because callers treat failures as non-cacheable and must avoid destructive overwrites.

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        - BadFunctionCallOutput if a local node is used and the contract for the
          token has no code. That means the chain is not synced
        """
        chunk_size, call_order = self._get_token_detection_chunk_size_call_order()
        tokens_per_address: dict[ChecksumEvmAddress, list[Asset]] = defaultdict(list)
        balances_per_address: DetectedTokenBalancesType = {}
        failed_addresses: set[ChecksumEvmAddress] = set()
        for address in addresses:
            query_result = self._query_chunks(
                address=address,
                tokens=tokens_to_check,
                chunk_size=chunk_size,
                call_order=call_order,
            )
            if query_result.had_failures is True:
                failed_addresses.add(address)
                log.warning(
                    f'{self.evm_inquirer.chain_name} token detection encountered query failures '
                    f'for address {address}. Skipping token-cache update for this address.',
                )
                continue

            tokens_per_address[address] = list(query_result.balances.keys())
            balances_per_address[address] = query_result.balances

        return tokens_per_address, failed_addresses, balances_per_address

    def query_tokens_for_addresses(
            self,
            addresses: Sequence[ChecksumEvmAddress],
    ) -> TokenBalancesType:
        """Queries token balances for a list of addresses
        Returns the token balances of each address and the usd prices of the tokens.

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        - BadFunctionCallOutput if a local node is used and the contract for the
          token has no code. That means the chain is not synced
        """
        addresses_to_balances: dict[ChecksumEvmAddress, dict[EvmToken, FVal]] = defaultdict(dict)
        all_tokens: set[EvmToken] = set()
        addresses_to_tokens: dict[ChecksumEvmAddress, list[EvmToken]] = {}
        chunk_size, call_order = self._get_token_detection_chunk_size_call_order()

        with self.db.conn.read_ctx() as cursor:
            for address in addresses:
                saved_list, _ = self.db.get_tokens_for_address(
                    cursor=cursor,
                    address=address,
                    blockchain=self.evm_inquirer.blockchain,
                    token_exceptions=self._per_chain_token_exceptions(),
                )
                if saved_list is None:
                    continue  # Do not query if we know the address has no tokens

                # get NFT tokens for address and ignore them from the query to avoid duplicates
                cursor.execute(
                    'SELECT identifier, blockchain FROM nfts WHERE owner_address=?',
                    (address,),
                )
                excluded_addresses = {
                    Nft(row[0]).evm_address for row in cursor
                    if SupportedBlockchain.deserialize(row[1]) == self.evm_inquirer.blockchain
                }
                token_list = [x for x in saved_list if x.evm_address not in excluded_addresses]
                all_tokens.update(token_list)
                addresses_to_tokens[address] = token_list

        tokens_with_balance = set()
        multicall_chunks = generate_multicall_chunks(
            addresses_to_tokens=addresses_to_tokens,
            chunk_length=chunk_size,
        )
        for chunk in multicall_chunks:
            new_balances = self._get_multicall_token_balances(
                chunk=chunk,
                call_order=call_order,
            )
            for address, balances in new_balances.items():
                for token, balance in balances.items():
                    if balance == ZERO:
                        continue  # skip any zero balance tokens

                    tokens_with_balance.add(token)
                    if token.token_kind == TokenKind.ERC721:
                        # For nfts the balance will be the total number of nfts the user owns from
                        # this collection. But any individual nft can only have a balance of one.
                        addresses_to_balances[address][token] = ONE
                    else:
                        addresses_to_balances[address][token] = balance

        token_price = cast('dict[EvmToken, Price]', Inquirer.find_main_currency_prices(list(tokens_with_balance)))  # noqa: E501
        return dict(addresses_to_balances), token_price

    def _get_token_exceptions(self) -> set[ChecksumEvmAddress]:
        """Returns a list of token addresses for which balances will not be queried"""
        with self.db.conn.read_ctx() as cursor:
            ignored_asset_ids = self.db.get_ignored_asset_ids(cursor=cursor)

        # TODO: Shouldn't this query be filtered in the DB?
        exceptions = set()
        for asset_id in ignored_asset_ids:  # don't query for the ignored tokens
            if (evm_details := asset_id_is_evm_token(asset_id)) is not None and evm_details[0] == self.evm_inquirer.chain_id:  # noqa: E501
                exceptions.add(evm_details[1])

        return exceptions | self._per_chain_token_exceptions()

    # -- methods to be implemented by child classes

    def _per_chain_token_exceptions(self) -> set[ChecksumEvmAddress]:
        """
        Returns a list of token addresses that will not be taken into account
        when performing token detection.

        Each chain needs to implement any chain-specific exceptions here.
        """
        return self.token_exceptions


class EvmTokensWithProxies(EvmTokens, ABC):
    def __init__(
            self,
            database: 'DBHandler',
            evm_inquirer: 'EvmNodeInquirer',
            token_exceptions: set[ChecksumEvmAddress] | None = None,
    ):
        super().__init__(database=database, evm_inquirer=evm_inquirer, token_exceptions=token_exceptions)  # noqa: E501
        self.evm_inquirer: EvmNodeInquirerWithProxies  # set explicit type

    def _query_new_tokens(self, addresses: Sequence[ChecksumEvmAddress]) -> None:
        super()._query_new_tokens(addresses)
        self.maybe_detect_proxies_tokens(addresses)

    def maybe_detect_proxies_tokens(self, addresses: Sequence[ChecksumEvmAddress]) -> None:  # pylint: disable=unused-argument
        """Subclasses may implement this method to detect tokens for proxies"""
        return None

    def _compute_detected_tokens_info(self, addresses: Sequence[ChecksumEvmAddress]) -> DetectedTokensType:  # noqa: E501
        """
        Generate a structure that contains information about the addresses that tokens
        were requested for.
        It generates a dictionary where key is an address and value is
        either a list of tokens or the timestamp of the last tokens query for that address.

        This specific function also combines ds proxies balances with the balances of the owners of
        the proxies.
        """
        addresses_info_without_proxies = super()._compute_detected_tokens_info(addresses)
        proxies_mapping = self.evm_inquirer.proxies_inquirer.get_accounts_having_proxy()

        addresses_info = {}
        with self.db.conn.read_ctx() as cursor:
            for (
                address,
                (detected_tokens_without_proxies, last_queried_ts_without_proxies),
            ) in addresses_info_without_proxies.items():
                # Creating new variables because modifying loop variables is not good
                detected_tokens = detected_tokens_without_proxies
                last_queried_timestamp = last_queried_ts_without_proxies
                proxy_last_queried_timestamp = None
                for proxy_type in ProxyType:
                    proxy_detected_tokens: set[EvmToken] = set()
                    if (proxy_addresses := proxies_mapping.get(proxy_type, {}).get(address)) is not None:  # noqa: E501
                        for proxy_address in proxy_addresses:
                            single_proxy_detected_tokens, proxy_last_queried_timestamp = self.db.get_tokens_for_address(  # noqa: E501
                                cursor=cursor,
                                address=proxy_address,
                                blockchain=self.evm_inquirer.blockchain,
                                token_exceptions=self._per_chain_token_exceptions(),
                            )
                            if single_proxy_detected_tokens:
                                proxy_detected_tokens |= set(single_proxy_detected_tokens)

                    if len(proxy_detected_tokens) != 0:
                        if detected_tokens_without_proxies is None:
                            detected_tokens = list(proxy_detected_tokens)
                        else:
                            detected_tokens = list(set(detected_tokens_without_proxies) | proxy_detected_tokens)  # noqa: E501

                    if proxy_last_queried_timestamp is not None:
                        if last_queried_ts_without_proxies is None:
                            last_queried_timestamp = proxy_last_queried_timestamp
                        else:
                            last_queried_timestamp = min(last_queried_ts_without_proxies, proxy_last_queried_timestamp)  # noqa: E501

                addresses_info[address] = (detected_tokens, last_queried_timestamp)

        return addresses_info
