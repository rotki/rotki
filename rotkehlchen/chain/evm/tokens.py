import logging
from abc import ABC
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, TypeVar, cast

from rotkehlchen.assets.asset import Asset, EvmToken, Nft
from rotkehlchen.chain.ethereum.utils import (
    token_normalized_value,
    token_normalized_value_decimals,
)
from rotkehlchen.chain.evm.decoding.uniswap.v3.constants import UNISWAP_V3_NFT_MANAGER_ADDRESSES
from rotkehlchen.chain.evm.types import WeightedNode, asset_id_is_evm_token
from rotkehlchen.chain.structures import EvmTokenDetectionData
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import ChainID, ChecksumEvmAddress, Price, SupportedBlockchain, Timestamp
from rotkehlchen.utils.misc import combine_dicts, get_chunks

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.node_inquirer import EvmNodeInquirerWithDSProxy
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

# maximum 32-bytes arguments in one call to a contract (either tokensBalance or multicall)
ETHERSCAN_MAX_ARGUMENTS_TO_CONTRACT = 110
ARBISCAN_MAX_ARGUMENTS_TO_CONTRACT = 25

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


def get_chunk_size_call_order(
        evm_inquirer: 'EvmNodeInquirer',
        web3_node_chunk_size: int = OTHER_MAX_TOKEN_CHUNK_LENGTH,
        etherscan_chunk_size: int = ETHERSCAN_MAX_ARGUMENTS_TO_CONTRACT,
        arbiscan_chunksize: int = ARBISCAN_MAX_ARGUMENTS_TO_CONTRACT,
) -> tuple[int, list[WeightedNode]]:
    """
    Return the max number of tokens that can be queried in a single call depending on whether we
    have a web3 node connected or we are going to use etherscan.
    We also return the nodes call order. In the case of having web3 nodes available we
    skip etherscan because chunk size is too big for etherscan.
    """
    if evm_inquirer.connected_to_any_web3():
        chunk_size = web3_node_chunk_size
        call_order = evm_inquirer.default_call_order(skip_etherscan=True)
    else:
        chunk_size = etherscan_chunk_size if evm_inquirer.chain_id != ChainID.ARBITRUM_ONE else arbiscan_chunksize  # noqa: E501
        call_order = [evm_inquirer.etherscan_node]

    return chunk_size, call_order


class EvmTokens(ABC):  # noqa: B024
    def __init__(
            self,
            database: 'DBHandler',
            evm_inquirer: 'EvmNodeInquirer',
    ):
        self.db = database
        self.evm_inquirer = evm_inquirer

    def get_token_balances(
            self,
            address: ChecksumEvmAddress,
            tokens: list[EvmTokenDetectionData],
            call_order: Sequence[WeightedNode] | None,
    ) -> dict[Asset, FVal]:
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
        balances: dict[Asset, FVal] = defaultdict(FVal)
        try:
            result = self.evm_inquirer.contract_scan.call(
                node_inquirer=self.evm_inquirer,
                method_name='tokens_balance',
                arguments=[address, [x.address for x in tokens]],
                call_order=call_order,
            )
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
                balances[Asset(token.identifier)] += normalized_balance
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
        for address, tokens in chunk:
            tokens_addrs = [token.evm_address for token in tokens]
            calls.append(
                (
                    self.evm_inquirer.contract_scan.address,
                    self.evm_inquirer.contract_scan.encode(
                        method_name='tokens_balance',
                        arguments=[address, tokens_addrs],
                    ),
                ),
            )
        results = self.evm_inquirer.multicall(
            calls=calls,
            call_order=call_order,
        )
        balances: dict[ChecksumEvmAddress, dict[EvmToken, FVal]] = defaultdict(lambda: defaultdict(FVal))  # noqa: E501
        for (address, tokens), result in zip(chunk, results, strict=True):
            decoded_result = self.evm_inquirer.contract_scan.decode(
                result=result,
                method_name='tokens_balance',
                arguments=[address, [token.evm_address for token in tokens]],
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
    ) -> dict[Asset, FVal]:
        """Processes token balance queries in batches of chunk_size to avoid hitting gas limits.
        Uses Asset objects directly instead of EvmToken to minimize database queries.
        """
        total_token_balances: dict[Asset, FVal] = defaultdict(FVal)
        chunks = get_chunks(tokens, n=chunk_size)
        for chunk in chunks:
            new_token_balances = self.get_token_balances(
                address=address,
                tokens=chunk,
                call_order=call_order,
            )
            total_token_balances = combine_dicts(total_token_balances, new_token_balances)
        return total_token_balances

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
        all_tokens = GlobalDBHandler.get_token_detection_data(
            chain_id=self.evm_inquirer.chain_id,
            exceptions=self._get_token_exceptions(),
        )
        self._detect_tokens(
            addresses=addresses,
            tokens_to_check=all_tokens,
        )

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

    def _detect_tokens(
            self,
            addresses: Sequence[ChecksumEvmAddress],
            tokens_to_check: list[EvmTokenDetectionData],
    ) -> None:
        """
        Detect tokens for the given addresses.

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        - BadFunctionCallOutput if a local node is used and the contract for the
          token has no code. That means the chain is not synced
        """
        chunk_size, call_order = get_chunk_size_call_order(self.evm_inquirer)
        for address in addresses:
            token_balances = self._query_chunks(
                address=address,
                tokens=tokens_to_check,
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
        chunk_size, call_order = get_chunk_size_call_order(self.evm_inquirer)

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
                addresses_to_balances[address].update(balances)

        token_usd_price = cast('dict[EvmToken, Price]', Inquirer.find_usd_prices(list(all_tokens)))
        return dict(addresses_to_balances), token_usd_price

    def _get_token_exceptions(self) -> set[ChecksumEvmAddress]:
        """Returns a list of token addresses for which balances will not be queried"""
        with self.db.conn.read_ctx() as cursor:
            ignored_asset_ids = self.db.get_ignored_asset_ids(cursor=cursor)

        # TODO: Shouldn't this query be filtered in the DB?
        exceptions = set()
        for asset_id in ignored_asset_ids:  # don't query for the ignored tokens
            if (evm_details := asset_id_is_evm_token(asset_id)) is not None and evm_details[0] == self.evm_inquirer.chain_id:  # noqa: E501
                exceptions.add(evm_details[1])

        # Exclude the Uniswap V3 NFT Manager address.
        # Without this exclusion, the balance logic reports a balance equal to the
        # number of Uniswap V3 positions held by the user for *each* position NFT.
        # Actual position balances are handled by the UniswapV3Balances class.
        if self.evm_inquirer.chain_id in UNISWAP_V3_NFT_MANAGER_ADDRESSES:
            exceptions.add(UNISWAP_V3_NFT_MANAGER_ADDRESSES[self.evm_inquirer.chain_id])

        return exceptions | self._per_chain_token_exceptions()

    # -- methods to be implemented by child classes

    def _per_chain_token_exceptions(self) -> set[ChecksumEvmAddress]:
        """
        Returns a list of token addresses that will not be taken into account
        when performing token detection.

        Each chain needs to implement any chain-specific exceptions here.
        """
        return set()


class EvmTokensWithDSProxy(EvmTokens, ABC):
    def __init__(
            self,
            database: 'DBHandler',
            evm_inquirer: 'EvmNodeInquirerWithDSProxy',
    ):
        super().__init__(database=database, evm_inquirer=evm_inquirer)
        self.evm_inquirer: EvmNodeInquirerWithDSProxy  # set explicit type

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
                if address in proxies_mapping:
                    proxy_address = proxies_mapping[address]
                    proxy_detected_tokens, proxy_last_queried_timestamp = self.db.get_tokens_for_address(  # noqa: E501
                        cursor=cursor,
                        address=proxy_address,
                        blockchain=self.evm_inquirer.blockchain,
                        token_exceptions=self._per_chain_token_exceptions(),
                    )

                    if proxy_detected_tokens is not None:
                        if detected_tokens_without_proxies is None:
                            detected_tokens = proxy_detected_tokens
                        else:
                            detected_tokens = list(set(detected_tokens_without_proxies + proxy_detected_tokens))  # noqa: E501

                    if proxy_last_queried_timestamp is not None:
                        if last_queried_ts_without_proxies is None:
                            last_queried_timestamp = proxy_last_queried_timestamp
                        else:
                            last_queried_timestamp = min(last_queried_ts_without_proxies, proxy_last_queried_timestamp)  # noqa: E501

                addresses_info[address] = (detected_tokens, last_queried_timestamp)

        return addresses_info
