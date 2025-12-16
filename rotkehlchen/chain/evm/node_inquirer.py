import itertools
import json
import logging
from collections import defaultdict
from collections.abc import Callable, Iterator, Sequence
from itertools import zip_longest
from typing import TYPE_CHECKING, Any, Literal, TypeVar, overload

import requests
from eth_abi.exceptions import DecodingError
from eth_typing.abi import ABI
from eth_utils.abi import get_abi_output_types
from web3 import Web3
from web3._utils.contracts import find_matching_event_abi
from web3._utils.filters import construct_event_filter_params
from web3.datastructures import MutableAttributeDict
from web3.exceptions import InvalidAddress, TransactionNotFound, Web3Exception
from web3.types import BlockIdentifier, FilterParams

from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.assets.utils import CHAIN_TO_WRAPPED_TOKEN
from rotkehlchen.chain.constants import DEFAULT_RPC_TIMEOUT, SAFE_BASIC_ABI
from rotkehlchen.chain.ethereum.constants import (
    ETHEREUM_ETHERSCAN_NODE_NAME,
)
from rotkehlchen.chain.ethereum.types import LogIterationCallback
from rotkehlchen.chain.ethereum.utils import MULTICALL_CHUNKS, should_update_protocol_cache
from rotkehlchen.chain.evm.constants import (
    DEFAULT_TOKEN_DECIMALS,
    ERC20_PROPERTIES,
    ERC20_PROPERTIES_NUM,
    ERC721_PROPERTIES,
    FAKE_GENESIS_TX_RECEIPT,
    GENESIS_HASH,
)
from rotkehlchen.chain.evm.contracts import EvmContract, EvmContracts
from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2_CHAINIDS_WITH_L1_FEES
from rotkehlchen.chain.evm.proxies_inquirer import EvmProxiesInquirer
from rotkehlchen.chain.evm.types import EvmIndexer, RemoteDataQueryStatus, WeightedNode
from rotkehlchen.chain.mixins.rpc_nodes import EVMRPCMixin
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.constants import ONE
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import (
    BlockchainQueryError,
    ChainNotSupported,
    EventNotInABI,
    NoAvailableIndexers,
    NotERC20Conformant,
    NotERC721Conformant,
    RemoteError,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.blockscout import Blockscout
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.externalapis.etherscan_like import EtherscanLikeApi, HasChainActivity
from rotkehlchen.externalapis.routescan import Routescan
from rotkehlchen.fval import FVal
from rotkehlchen.greenlets.manager import GreenletManager
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_address,
    deserialize_evm_transaction,
    deserialize_int_from_hex,
)
from rotkehlchen.serialization.serialize import process_result
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    SUPPORTED_EVM_CHAINS_TYPE,
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    EvmInternalTransaction,
    EvmTransaction,
    EVMTxHash,
    Timestamp,
    TokenKind,
)
from rotkehlchen.utils.data_structures import LRUCacheWithRemove
from rotkehlchen.utils.misc import from_wei, get_chunks
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn, protect_with_lock

if TYPE_CHECKING:
    from rotkehlchen.chain.gnosis.transactions import GnosisWithdrawalsQueryParameters
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

T = TypeVar('T')


def _connect_task_prefix(chain_name: str) -> str:
    """Helper function to create the connection task greenlet name"""
    return f'Attempt connection to {chain_name} node'


WEB3_LOGQUERY_BLOCK_RANGE = 250000
MAX_NODE_LOG_QUERY_CALLS = 500  # max queries for a node that can query logs from up to 1000/10_000 blocks  # noqa: E501


def _query_web3_get_logs(
        web3: Web3,
        filter_args: FilterParams,
        from_block: int,
        to_block: int | Literal['latest'],
        contract_address: ChecksumEvmAddress,
        event_name: str,
        argument_filters: dict[str, Any],
        initial_block_range: int,
        log_iteration_cb: LogIterationCallback | None = None,
        log_iteration_cb_arguments: 'GnosisWithdrawalsQueryParameters | None' = None,
) -> list[dict[str, Any]]:
    until_block = web3.eth.block_number if to_block == 'latest' else to_block
    events: list[dict[str, Any]] = []
    start_block = from_block
    block_range = initial_block_range

    while start_block <= until_block:
        filter_args['fromBlock'] = start_block
        end_block = min(start_block + block_range, until_block)
        filter_args['toBlock'] = end_block
        log.debug(
            'Querying web3 node for contract event',
            contract_address=contract_address,
            event_name=event_name,
            argument_filters=argument_filters,
            from_block=filter_args['fromBlock'],
            to_block=filter_args['toBlock'],
        )
        # As seen in https://github.com/rotki/rotki/issues/1787, the json RPC, if it
        # is infura can throw an error here which we can only parse by catching the  exception
        try:
            new_events_web3: list[dict[str, Any]] = [dict(x) for x in web3.eth.get_logs(filter_args)]  # noqa: E501
        except (Web3Exception, ValueError, KeyError) as e:
            if isinstance(e, ValueError | Web3Exception):
                try:
                    decoded_error = json.loads(str(e).replace("'", '"'))
                except json.JSONDecodeError:
                    # reraise the value error if the error is not json
                    raise e from None

                msg = decoded_error.get('message', '')
            else:  # temporary hack for key error seen from pokt
                msg = 'query returned more than 10000 results'

            # errors from: https://infura.io/docs/ethereum/json-rpc/eth-getLogs
            if msg == 'query returned more than 10000 results':
                if (until_block - start_block) // 10_000 > MAX_NODE_LOG_QUERY_CALLS:
                    log.debug(f'Querying logs with a range of 10_000 from {web3} will take too much time. Stopping here')  # noqa: E501
                    raise

                block_range = initial_block_range = 9999  # ensure that block range doesn't get reset to a range bigger than what is allowed for this node  # noqa: E501
                continue
            elif msg == 'eth_getLogs is limited to a 1000 blocks range':  # seen in https://1rpc.io/gnosis  # noqa: E501
                if (until_block - start_block) // 1_000 > MAX_NODE_LOG_QUERY_CALLS:
                    log.debug(f'Querying logs with a range of 1000 from {web3} will take too much time. Stopping here')  # noqa: E501
                    raise

                block_range = initial_block_range = 999
                continue
            elif msg == 'query timeout exceeded':
                block_range //= 2
                if block_range < 50:
                    raise  # stop retrying if block range gets too small
                # repeat the query with smaller block range
                continue
            else:  # else, well we tried .. reraise the error
                raise

        # Turn all HexBytes into hex strings
        for e_idx, event in enumerate(new_events_web3):
            new_events_web3[e_idx]['blockHash'] = event['blockHash'].to_0x_hex()
            new_events_web3[e_idx]['data'] = event['data'].to_0x_hex()
            new_topics = [topic.to_0x_hex() for topic in event['topics']]
            new_events_web3[e_idx]['topics'] = new_topics
            new_events_web3[e_idx]['transactionHash'] = event['transactionHash'].to_0x_hex()

        if log_iteration_cb is not None:
            log_iteration_cb(
                last_block_queried=end_block,
                filters=argument_filters,
                new_events=new_events_web3,
                cb_arguments=log_iteration_cb_arguments,
            )

        start_block = end_block + 1
        events.extend(new_events_web3)
        # end of the loop, end of 1 query. Reset the block range to max
        block_range = initial_block_range

    return events


class EvmNodeInquirer(EVMRPCMixin, LockableQueryMixIn):
    """Class containing generic functionality for querying evm nodes

    The child class must implement the following methods:
    - _have_archive
    - _is_pruned
    - get_blocknumber_by_time

    The child class may optionally implement the following:
    - logquery_block_range
    """
    methods_that_query_past_data = (
        '_get_transaction_receipt',
        '_get_transaction_by_hash',
        '_get_logs',
    )

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: Etherscan,
            routescan: Routescan,
            blockchain: SUPPORTED_EVM_CHAINS_TYPE,
            contracts: EvmContracts,
            contract_scan: 'EvmContract',
            contract_multicall: 'EvmContract',
            native_token: CryptoAsset,
            rpc_timeout: int = DEFAULT_RPC_TIMEOUT,
            blockscout: Blockscout | None = None,
    ) -> None:
        self.greenlet_manager = greenlet_manager
        self.database = database
        self.blockchain = blockchain
        self.etherscan = etherscan
        self.routescan = routescan
        self.blockscout = blockscout
        self.available_indexers: dict[EvmIndexer, Blockscout | Etherscan | Routescan | None] = {
            EvmIndexer.ETHERSCAN: self.etherscan,
            EvmIndexer.BLOCKSCOUT: self.blockscout,
            EvmIndexer.ROUTESCAN: self.routescan,
        }
        self.contracts = contracts
        self.rpc_timeout = rpc_timeout
        self.chain_id: SUPPORTED_CHAIN_IDS = blockchain.to_chain_id()
        self.chain_name = self.chain_id.to_name()
        self.native_token = native_token
        self.wrapped_native_token = CHAIN_TO_WRAPPED_TOKEN[self.blockchain].resolve_to_evm_token()
        # BalanceScanner from mycrypto: https://github.com/MyCryptoHQ/eth-scan
        self.contract_scan = contract_scan
        # Multicall from MakerDAO: https://github.com/makerdao/multicall/
        self.contract_multicall = contract_multicall
        # keep a cache per chain id of timestamp to block to avoid querying multiple times
        # the same information. Remove from here with
        # https://github.com/rotki/rotki/issues/9998
        self.timestamp_to_block_cache: dict[ChainID, LRUCacheWithRemove[Timestamp, int]] = defaultdict(lambda: LRUCacheWithRemove(maxsize=32))  # noqa: E501

        # A cache for erc20 and erc721 contract info to not requery the info
        self.contract_info_erc20_cache: LRUCacheWithRemove[ChecksumEvmAddress, dict[str, Any]] = LRUCacheWithRemove(maxsize=1024)  # noqa: E501
        self.contract_info_erc721_cache: LRUCacheWithRemove[ChecksumEvmAddress, dict[str, Any]] = LRUCacheWithRemove(maxsize=512)  # noqa: E501
        # cache used by is_safe_proxy_or_eoa
        self._known_accounts_cache: LRUCacheWithRemove[ChecksumEvmAddress, bool] = LRUCacheWithRemove(maxsize=50)  # noqa: E501
        LockableQueryMixIn.__init__(self)
        EVMRPCMixin.__init__(self)
        # Log the available nodes so we have extra information when debugging connection errors.
        nodes = '\n'.join([str(x.serialize()) for x in self.default_call_order()])  # variable because \ is not valid in f-strings  # noqa: E501
        log.debug(f'RPC nodes at startup {nodes}')

    def get_multi_balance(
            self,
            accounts: Sequence[ChecksumEvmAddress],
            call_order: Sequence[WeightedNode] | None = None,
    ) -> dict[ChecksumEvmAddress, FVal]:
        """Returns a dict with keys being accounts and balances in the chain native token.

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
          there is a problem with its query.
        """
        balances: dict[ChecksumEvmAddress, FVal] = {}
        if len(accounts) == 0:
            return balances

        log.debug(
            f'Querying {self.chain_name} chain for {self.blockchain.serialize()} balance',
            eth_addresses=accounts,
        )
        result = self.contract_scan.call(
            node_inquirer=self,
            method_name='ether_balances',
            arguments=[accounts],
            call_order=call_order if call_order is not None else self.default_call_order(),
        )
        balances = {}
        for idx, account in enumerate(accounts):
            balances[account] = from_wei(result[idx])
        return balances

    def get_historical_balance(
            self,
            address: ChecksumEvmAddress,
            block_number: int,
            web3: Web3 | None = None,
    ) -> FVal | None:
        """Attempts to get the historical eth balance using the node provided.

        If `web3` is None, it uses the local own node.
        Returns None if there is no local node or node cannot query historical balance.
        """
        if (web3 := web3 if web3 is not None else self.get_own_node()) is None:
            return None

        try:
            result = web3.eth.get_balance(address, block_identifier=block_number)
        except (
                requests.RequestException,
                BlockchainQueryError,
                KeyError,  # saw this happen inside web3.py if resulting json contains unexpected key. Happened with mycrypto's node  # noqa: E501
                Web3Exception,
                ValueError,  # can still happen in web3py v6 for missing trieerror. Essentially historical balance call  # noqa: E501
        ):
            return None

        try:
            balance = from_wei(FVal(result))
        except ValueError:
            return None

        return balance

    def _have_archive(self, web3: Web3) -> bool:
        """Returns a boolean representing if node is an archive one."""
        address_to_check, block_to_check, expected_balance = self._get_archive_check_data()
        return self.get_historical_balance(
            address=address_to_check,
            block_number=block_to_check,
            web3=web3,
        ) == expected_balance

    def _query(self, method: Callable, call_order: Sequence[WeightedNode], **kwargs: Any) -> Any:
        """Queries evm related data by performing a query of the provided method to all given nodes

        The first node in the call order that gets a successful response returns.
        If none get a result then RemoteError is raised
        """
        for node_idx, weighted_node in enumerate(call_order):
            node_info = weighted_node.node_info
            if (rpc_node := self.rpc_mapping.get(node_info, None)) is None:
                if node_info.name in self.failed_to_connect_nodes:
                    continue

                if node_info.name != ETHEREUM_ETHERSCAN_NODE_NAME:
                    success, _ = self.attempt_connect(node=node_info)
                    if success is False:
                        self.failed_to_connect_nodes.add(node_info.name)
                        continue

                    if (rpc_node := self.rpc_mapping.get(node_info, None)) is None:
                        log.error(f'Unexpected missing node {node_info} at {self.chain_id}')
                        continue

            if rpc_node is not None and ((
                method.__name__ in self.methods_that_query_past_data and
                rpc_node.is_pruned is True
            ) or (
                kwargs.get('block_identifier', 'latest') != 'latest' and
                rpc_node.is_archive is False
            )):
                # If the block_identifier is different from 'latest'
                # this query should be routed to an archive node
                continue

            try:
                web3 = rpc_node.rpc_client if rpc_node is not None else None
                result = method(web3, **kwargs)
            except TransactionNotFound:
                if kwargs.get('must_exist', False) is True:
                    continue  # try other nodes, as transaction has to exist
                return None
            except InvalidAddress as e:
                raise RemoteError(  # no need to try other nodes since its not a node problem.
                    f'Failed to query {node_info.name} for {method!s}: '
                    f'non-checksum address {e.args[1]}',
                ) from e
            except requests.Timeout as e:  # Add node to failed_to_connect_nodes to prevent repeatedly timing out on the same node.  # noqa: E501
                log.warning(
                    f'Timed out while querying {node_info.name} for '
                    f'{method.__name__}: {e!s}. Skipping this node in future queries.',
                )
                self.failed_to_connect_nodes.add(node_info.name)
                self.rpc_mapping.pop(node_info, None)
                continue
            except (
                    RemoteError,
                    requests.exceptions.RequestException,
                    BlockchainQueryError,
                    Web3Exception,
                    TypeError,  # happened at the web3 level calling `apply_result_formatters` when the RPC node returned `None` in the response's result # noqa: E501
                    ValueError,  # not removing yet due to possibility of raising from missing trie error  # noqa: E501
                    AttributeError,  # happened at the web3 level when response is a string instead of dict # noqa: E501
                    json.JSONDecodeError,  # happens when RPC returns empty or invalid JSON responses # noqa: E501
            ) as e:
                log.warning(
                    f'Failed to query {node_info.name} with position on the query list {node_idx} '
                    f'for {method.__name__} due to {e!s}',
                )
                # Catch all possible errors here and just try next node call
                continue

            return result

        # no node in the call order list was successfully queried
        log.error(
            f'Failed to query {method.__name__} after trying the following '
            f'nodes: {[x.node_info.name for x in call_order]}. Call parameters were {kwargs}',
        )
        raise RemoteError(f'Error querying information from {self.blockchain!s}. Checks logs to obtain more information')  # noqa: E501

    def _get_latest_block_number(self, web3: Web3 | None) -> int:
        if web3 is not None:
            return web3.eth.block_number

        # else
        return self.etherscan.get_latest_block_number(chain_id=self.chain_id)

    def get_latest_block_number(self, call_order: Sequence[WeightedNode] | None = None) -> int:
        return self._query(
            method=self._get_latest_block_number,
            call_order=call_order if call_order is not None else self.default_call_order(),
        )

    def get_block_by_number(
            self,
            num: int,
            call_order: Sequence[WeightedNode] | None = None,
    ) -> dict[str, Any]:
        return self._query(
            method=self._get_block_by_number,
            call_order=call_order if call_order is not None else self.default_call_order(),
            num=num,
        )

    def _get_block_by_number(self, web3: Web3 | None, num: int) -> dict[str, Any]:
        """Returns the block object corresponding to the given block number

        May raise:
        - RemoteError if an external service such as Etherscan is queried and
        there is a problem with its query.
        - BlockNotFound if number used to lookup the block can't be found. Raised
        by web3.eth.get_block().
        """
        if web3 is None:
            return self.etherscan.get_block_by_number(
                chain_id=self.chain_id,
                block_number=num,
            )

        block_data: MutableAttributeDict = MutableAttributeDict(web3.eth.get_block(num))  # type: ignore # pylint: disable=no-member
        block_data['hash'] = block_data['hash'].to_0x_hex()
        return dict(block_data)

    def get_code(
            self,
            account: ChecksumEvmAddress,
            call_order: Sequence[WeightedNode] | None = None,
    ) -> str:
        return self._query(
            method=self._get_code,
            call_order=call_order if call_order is not None else self.default_call_order(),
            account=account,
        )

    def _get_code(self, web3: Web3 | None, account: ChecksumEvmAddress) -> str:
        """Gets the deployment bytecode at the given address as a 0x hex string

        May raise:
        - RemoteError if Etherscan is used and there is a problem querying it or
        parsing its response
        """
        if web3 is None:
            return self.etherscan.get_code(chain_id=self.chain_id, account=account)

        return web3.eth.get_code(account).to_0x_hex()

    def _call_contract_etherscan(
            self,
            contract_address: ChecksumEvmAddress,
            abi: ABI,
            method_name: str,
            arguments: list[Any] | None = None,
    ) -> Any:
        """Performs an eth_call to an evm contract via etherscan

        May raise:
        - RemoteError if there is a problem with
        reaching etherscan or with the returned result
        """
        web3 = Web3()
        given_arguments = arguments or []
        contract = web3.eth.contract(address=contract_address, abi=abi)
        input_data = contract.encode_abi(method_name, args=given_arguments)
        result = self.etherscan.eth_call(
            chain_id=self.chain_id,
            to_address=contract_address,
            input_data=input_data,
        )
        if result == '0x':
            raise BlockchainQueryError(
                f'Error doing call on contract {contract_address} for {method_name} '
                f'and chain {self.chain_name} with arguments: {arguments!s} '
                f'via etherscan. Returned 0x result',
            )

        fn_abi = contract._find_matching_fn_abi(
            method_name,
            *given_arguments,
        )
        output_types = get_abi_output_types(fn_abi)
        output_data = web3.codec.decode(output_types, bytes.fromhex(result[2:]))

        if len(output_data) == 1:
            # due to https://github.com/PyCQA/pylint/issues/4114
            return output_data[0]
        return output_data

    def call_contract(
            self,
            contract_address: ChecksumEvmAddress,
            abi: ABI,
            method_name: str,
            arguments: list[Any] | None = None,
            call_order: Sequence[WeightedNode] | None = None,
            block_identifier: BlockIdentifier = 'latest',
    ) -> Any:
        return self._query(
            method=self._call_contract,
            call_order=call_order if call_order is not None else self.default_call_order(),
            contract_address=contract_address,
            abi=abi,
            method_name=method_name,
            arguments=arguments,
            block_identifier=block_identifier,
        )

    def _call_contract(
            self,
            web3: Web3 | None,
            contract_address: ChecksumEvmAddress,
            abi: ABI,
            method_name: str,
            arguments: list[Any] | None = None,
            block_identifier: BlockIdentifier = 'latest',
    ) -> Any:
        """Performs an eth_call to an evm contract

        May raise:
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result
        - BlockchainQueryError if web3 is used and there is a VM execution error
        """
        if web3 is None:
            return self._call_contract_etherscan(
                contract_address=contract_address,
                abi=abi,
                method_name=method_name,
                arguments=arguments,
            )

        contract = web3.eth.contract(address=contract_address, abi=abi)
        try:
            method = getattr(contract.caller(block_identifier=block_identifier), method_name)
            result = method(*arguments or [])
        except InvalidAddress:
            raise  # propagate to _query() where it's handled properly
        except (Web3Exception, ValueError) as e:
            raise BlockchainQueryError(
                f'Error doing call on contract {contract_address}: {e!s}',
            ) from e
        return result

    def _get_transaction_receipt(
            self,
            web3: Web3 | None,
            tx_hash: EVMTxHash,
            must_exist: bool = False,
    ) -> dict[str, Any] | None:
        if tx_hash == GENESIS_HASH:
            return FAKE_GENESIS_TX_RECEIPT
        if web3 is None:
            tx_receipt = self.etherscan.get_transaction_receipt(
                chain_id=self.chain_id,
                tx_hash=tx_hash,
            )
            if tx_receipt is None:
                if must_exist:  # fail, so other nodes can be tried
                    raise RemoteError(f'Querying for {self.chain_name} receipt {tx_hash.hex()} returned None')  # noqa: E501

                return None  # else it does not exist

            try:
                # Turn hex numbers to int
                block_number = int(tx_receipt['blockNumber'], 16)
                tx_receipt['blockNumber'] = block_number
                tx_receipt['cumulativeGasUsed'] = int(tx_receipt['cumulativeGasUsed'], 16)
                tx_receipt['gasUsed'] = int(tx_receipt['gasUsed'], 16)
                tx_receipt['status'] = int(tx_receipt.get('status', '0x1'), 16)
                tx_index = int(tx_receipt['transactionIndex'], 16)
                tx_receipt['transactionIndex'] = tx_index
                for receipt_log in tx_receipt['logs']:
                    receipt_log['blockNumber'] = block_number
                    receipt_log['logIndex'] = deserialize_int_from_hex(
                        symbol=receipt_log['logIndex'],
                        location='etherscan tx receipt',
                    )
                    receipt_log['transactionIndex'] = tx_index
                # This is only implemented for some evm chains
                self._additional_receipt_processing(tx_receipt)
            except (DeserializationError, Web3Exception, ValueError, KeyError) as e:
                msg = str(e)
                if isinstance(e, KeyError):
                    msg = f'missing key {msg}'
                log.error(
                    f'Couldnt deserialize transaction receipt {tx_receipt} data from '
                    f'etherscan due to {msg}',
                )
                raise RemoteError(
                    f'Couldnt deserialize transaction receipt data from etherscan '
                    f'due to {msg}. Check logs for details',
                ) from e

            if must_exist and tx_receipt is None:  # fail, so other nodes can be tried
                raise RemoteError(f'Querying for {self.chain_name} receipt {tx_hash.hex()} returned None')  # noqa: E501

            return tx_receipt

        # Can raise TransactionNotFound if the user's node is pruned and transaction is old
        try:
            tx_receipt = web3.eth.get_transaction_receipt(tx_hash)  # type: ignore
        except TransactionNotFound as e:
            if must_exist:  # fail, so other nodes can be tried
                raise RemoteError(f'Querying for {self.chain_name} receipt {tx_hash.hex()} returned None') from e  # noqa: E501

            raise  # else re-raise e

        return process_result(tx_receipt)

    def maybe_get_transaction_receipt(
            self,
            tx_hash: EVMTxHash,
            call_order: Sequence[WeightedNode] | None = None,
            must_exist: bool = False,
    ) -> dict[str, Any] | None:
        return self._query(
            method=self._get_transaction_receipt,
            call_order=call_order if call_order is not None else self.default_call_order(),
            tx_hash=tx_hash,
            must_exist=must_exist,
        )

    def get_transaction_receipt(
            self,
            tx_hash: EVMTxHash,
            call_order: Sequence[WeightedNode] | None = None,
    ) -> dict[str, Any]:
        """Retrieves the transaction receipt for the tx_hash provided.

        This method assumes the tx_hash is present on-chain,
        and we are connected to at least one node that can retrieve it.
        """
        tx_receipt = self.maybe_get_transaction_receipt(
            call_order=call_order if call_order is not None else self.default_call_order(),
            tx_hash=tx_hash,
            must_exist=True,
        )
        if tx_receipt is None:
            raise RemoteError(f'{self.chain_name} tx_receipt should exist for {tx_hash.hex()}')
        return tx_receipt

    def _get_transaction_by_hash(
            self,
            web3: Web3 | None,
            tx_hash: EVMTxHash,
            must_exist: bool = False,
    ) -> tuple[EvmTransaction, dict[str, Any]] | None:
        if web3 is None:
            tx_data = self.etherscan.get_transaction_by_hash(
                chain_id=self.chain_id,
                tx_hash=tx_hash,
            )
        else:
            tx_data = web3.eth.get_transaction(tx_hash)  # type: ignore
        if tx_data is None:
            if must_exist:  # fail, so other nodes can be tried
                raise RemoteError(f'Querying for {self.chain_name} transaction {tx_hash.hex()} returned None')  # noqa: E501

            return None  # else it does not exist

        try:
            transaction, receipt_data = deserialize_evm_transaction(
                data=tx_data,
                internal=False,
                chain_id=self.chain_id,
                evm_inquirer=self,
            )
        except (DeserializationError, ValueError) as e:
            raise RemoteError(
                f'Couldnt deserialize evm transaction data from {tx_data}. Error: {e!s}',
            ) from e

        if receipt_data is None:
            raise RemoteError(f'{self.chain_name} transaction {tx_hash.hex()} receipt_data is expected to exist')  # noqa: E501  # as etherscan getTransactionByHash does not contains gasUsed'
        return transaction, receipt_data

    def maybe_get_transaction_by_hash(
            self,
            tx_hash: EVMTxHash,
            call_order: Sequence[WeightedNode] | None = None,
            must_exist: bool = False,
    ) -> tuple[EvmTransaction, dict[str, Any]] | None:
        """Gets transaction by hash and raw receipt data"""
        return self._query(
            method=self._get_transaction_by_hash,
            call_order=call_order if call_order is not None else self.default_call_order(),
            tx_hash=tx_hash,
            must_exist=must_exist,
        )

    def get_transaction_by_hash(
            self,
            tx_hash: EVMTxHash,
            call_order: Sequence[WeightedNode] | None = None,
    ) -> tuple[EvmTransaction, dict[str, Any]]:
        """Retrieves information about a transaction from its hash.

        This method assumes the tx_hash is present on-chain,
        and we are connected to at least 1 node that can retrieve it.
        """
        result = self.maybe_get_transaction_by_hash(
            call_order=call_order if call_order is not None else self.default_call_order(),
            tx_hash=tx_hash,
            must_exist=True,
        )
        if result is None:
            raise RemoteError(f'{self.chain_name} transaction {tx_hash.hex()} is expected to exist')  # noqa: E501

        return result

    def get_logs(
            self,
            contract_address: ChecksumEvmAddress,
            abi: ABI,
            event_name: str,
            argument_filters: dict[str, Any],
            from_block: int,
            to_block: int | Literal['latest'] = 'latest',
            call_order: Sequence[WeightedNode] | None = None,
            log_iteration_cb: LogIterationCallback | None = None,
            log_iteration_cb_arguments: 'GnosisWithdrawalsQueryParameters | None' = None,
    ) -> list[dict[str, Any]]:
        if call_order is None:  # Default call order for logs
            call_order = [self.etherscan_node]
            if (node_info := self.get_own_node_info()) is not None:
                call_order.append(
                    WeightedNode(
                        node_info=node_info,
                        active=True,
                        weight=ONE,
                    ),
                )
        return self._query(
            method=self._get_logs,
            call_order=call_order,
            contract_address=contract_address,
            abi=abi,
            event_name=event_name,
            argument_filters=argument_filters,
            from_block=from_block,
            to_block=to_block,
            log_iteration_cb=log_iteration_cb,
            log_iteration_cb_arguments=log_iteration_cb_arguments,
        )

    def _get_logs(
            self,
            web3: Web3 | None,
            contract_address: ChecksumEvmAddress,
            abi: ABI,
            event_name: str,
            argument_filters: dict[str, Any],
            from_block: int,
            to_block: int | Literal['latest'] = 'latest',
            log_iteration_cb: LogIterationCallback | None = None,
            log_iteration_cb_arguments: 'GnosisWithdrawalsQueryParameters | None' = None,
    ) -> list[dict[str, Any]]:
        """Queries logs of an evm contract
        May raise:

        - EventNotInABI if the given event is not in the ABI
        - RemoteError if etherscan is used and there is a problem with
        reaching it or with the returned result
        """
        try:
            event_abi = find_matching_event_abi(abi=abi, event_name=event_name)
        except ValueError as e:
            raise EventNotInABI from e

        _, filter_args = construct_event_filter_params(
            event_abi=event_abi,
            abi_codec=Web3().codec,
            contract_address=contract_address,
            argument_filters=argument_filters,
            from_block=from_block,
            to_block=to_block,
        )

        if event_abi.get('anonymous', False):
            # web3.py does not handle the anonymous events correctly and adds the first topic
            filter_args['topics'] = filter_args['topics'][1:]  # pyright: ignore  # I think FilterParams is not well defined. It always has topics
        events: list[dict[str, Any]] = []
        start_block = from_block

        log.debug(f'Ready to query logs for {filter_args} at {contract_address} ({self.chain_id}) from {start_block} to {to_block}')  # noqa: E501
        if web3 is not None:
            events = _query_web3_get_logs(
                web3=web3,
                filter_args=filter_args,
                from_block=from_block,
                to_block=to_block,
                contract_address=contract_address,
                event_name=event_name,
                argument_filters=argument_filters,
                initial_block_range=self.logquery_block_range(web3=web3, contract_address=contract_address),  # noqa: E501
                log_iteration_cb=log_iteration_cb,
                log_iteration_cb_arguments=log_iteration_cb_arguments,
            )
        else:  # etherscan
            until_block = (
                self.etherscan.get_latest_block_number(self.chain_id) if to_block == 'latest' else to_block  # noqa: E501
            )
            blocks_step = 300000
            while start_block <= until_block:
                while True:  # loop to continuously reduce block range if need b
                    end_block = min(start_block + blocks_step, until_block)
                    try:
                        new_events = self.etherscan.get_logs(
                            chain_id=self.chain_id,
                            contract_address=contract_address,
                            topics=filter_args['topics'],  # type: ignore
                            from_block=start_block,
                            to_block=end_block,
                        )
                    except RemoteError as e:
                        if 'Please select a smaller result dataset' in str(e):

                            blocks_step //= 2
                            if blocks_step < 100:
                                raise  # stop trying
                            # else try with the smaller step
                            continue

                        # else some other error
                        raise

                    break  # we must have a result

                # Turn all Hex ints to ints
                for e_idx, event in enumerate(new_events):
                    try:
                        block_number = deserialize_int_from_hex(
                            symbol=event['blockNumber'],
                            location='etherscan log query',
                        )
                        log_index = deserialize_int_from_hex(
                            symbol=event['logIndex'],
                            location='etherscan log query',
                        )
                        # Try to see if the event is a duplicate that got returned
                        # in the previous iteration
                        for previous_event in reversed(events):
                            if previous_event['blockNumber'] < block_number:
                                break

                            same_event = (
                                previous_event['logIndex'] == log_index and
                                previous_event['transactionHash'] == event['transactionHash']
                            )
                            if same_event:
                                events.pop()

                        new_events[e_idx]['address'] = deserialize_evm_address(
                            event['address'],
                        )
                        new_events[e_idx]['blockNumber'] = block_number
                        new_events[e_idx]['timeStamp'] = deserialize_int_from_hex(
                            symbol=event['timeStamp'],
                            location='etherscan log query',
                        )
                        new_events[e_idx]['gasPrice'] = deserialize_int_from_hex(
                            symbol=event['gasPrice'],
                            location='etherscan log query',
                        )
                        new_events[e_idx]['gasUsed'] = deserialize_int_from_hex(
                            symbol=event['gasUsed'],
                            location='etherscan log query',
                        )
                        new_events[e_idx]['logIndex'] = log_index
                        new_events[e_idx]['transactionIndex'] = deserialize_int_from_hex(
                            symbol=event['transactionIndex'],
                            location='etherscan log query',
                        )
                    except DeserializationError as e:
                        raise RemoteError(
                            'Couldnt decode an etherscan event due to {str(e)}}',
                        ) from e

                if log_iteration_cb is not None:
                    log_iteration_cb(
                        last_block_queried=end_block,
                        filters=argument_filters,
                        new_events=new_events,
                        cb_arguments=log_iteration_cb_arguments,
                    )

                # etherscan will only return 1000 events in one go. If more than 1000
                # are returned such as when no filter args are provided then continue
                # the query from the last block
                if len(new_events) == 1000:
                    start_block = new_events[-1]['blockNumber']
                else:
                    start_block = end_block + 1
                events.extend(new_events)

        return events

    def multicall(
            self,
            calls: list[tuple[ChecksumEvmAddress, str]],
            # only here to comply with multicall_2
            require_success: bool = True,  # pylint: disable=unused-argument
            call_order: Sequence['WeightedNode'] | None = None,
            block_identifier: BlockIdentifier = 'latest',
            calls_chunk_size: int = MULTICALL_CHUNKS,
    ) -> Any:
        """Uses MULTICALL contract. Failure of one call is a failure of the entire multicall.
        source: https://etherscan.io/address/0xeefBa1e63905eF1D7ACbA5a8513c70307C1cE441#code
        Can raise:
        - RemoteError
        """
        calls_chunked = list(get_chunks(calls, n=calls_chunk_size))
        output = []
        for call_chunk in calls_chunked:
            multicall_result = self.contract_multicall.call(
                node_inquirer=self,
                method_name='aggregate',
                arguments=[call_chunk],
                call_order=call_order,
                block_identifier=block_identifier,
            )
            _, chunk_output = multicall_result
            output += chunk_output
        return output

    def multicall_2(
            self,
            calls: list[tuple[ChecksumEvmAddress, str]],
            require_success: bool,
            call_order: Sequence['WeightedNode'] | None = None,
            block_identifier: BlockIdentifier = 'latest',
            # only here to comply with multicall
            calls_chunk_size: int = MULTICALL_CHUNKS,  # pylint: disable=unused-argument
    ) -> list[tuple[bool, bytes]]:
        """
        Uses MULTICALL_2 contract. If require success is set to False any call in the list
        of calls is allowed to fail.
        source: https://etherscan.io/address/0x5BA1e12693Dc8F9c48aAD8770482f4739bEeD696#code"""
        return self.contract_multicall.call(
            node_inquirer=self,
            method_name='tryAggregate',
            arguments=[require_success, calls],
            call_order=call_order,
            block_identifier=block_identifier,
        )

    def multicall_specific(
            self,
            contract: 'EvmContract',
            method_name: str,
            arguments: list[Any],
            call_order: Sequence['WeightedNode'] | None = None,
            decode_result: bool = True,
    ) -> Any:
        calls = [(
            contract.address,
            contract.encode(method_name=method_name, arguments=i),
        ) for i in arguments]
        output = self.multicall(calls, True, call_order)
        if decode_result is False:
            return output
        return [contract.decode(x, method_name, arguments[0]) for x in output]

    def get_multiple_erc20_contract_info(self, addresses: list[ChecksumEvmAddress]) -> None:
        """Query the token information for multiple ERC20 addresses and save them in cache"""
        if len(addresses) == 0:
            return

        contract = EvmContract(address=addresses[0], abi=self.contracts.erc20_abi, deployed_block=0)  # noqa: E501

        for addresses_chunk in get_chunks(addresses, 8):  # chunk number seems to be highest that can work with etherscan url limit  # noqa: E501
            calls = [(address, contract.encode(method_name=prop)) for address in addresses_chunk for prop in ERC20_PROPERTIES]  # noqa: E501

            try:
                # Output contains call status and result
                output = self.multicall_2(require_success=False, calls=calls)
            except RemoteError:
                # If something happens in the connection the output should have
                # the same length as the tuple of properties * addresses
                output = [(False, b'')] * ERC20_PROPERTIES_NUM * len(addresses_chunk)

            for idx, single_output in enumerate(get_chunks(output, ERC20_PROPERTIES_NUM)):
                address = addresses_chunk[idx]
                try:
                    info = self._process_and_create_erc20_info(
                        output=single_output,
                        address=address,
                    )
                except NotERC20Conformant:
                    log.warning(f'{address} on {self.chain_name} is not a valid ERC20 token. Skipping')  # noqa: E501
                    continue

                self.contract_info_erc20_cache.add(address, info)

    def _process_and_create_erc20_info(
            self,
            output: list[tuple[bool, bytes]],
            address: ChecksumEvmAddress,
    ) -> dict[str, Any]:
        """May raise:
        - NotERC20Conformant
        """
        info: dict[str, Any] = {}
        contract = EvmContract(address=address, abi=self.contracts.erc20_abi, deployed_block=0)
        try:
            decoded = self._process_contract_info(
                output=output,
                properties=ERC20_PROPERTIES,
                contract=contract,
                token_kind=TokenKind.ERC20,
            )
        except (OverflowError, DecodingError) as e:
            # This can happen when contract follows the ERC20 standard methods
            # but name and symbol return bytes instead of string. UNIV1 LP is such a case
            # It can also happen if the method is missing and they are all hitting
            # the fallback function. old WETH contract is such a case
            log.error(
                f'{address} failed to decode as ERC20 token. '
                f'Trying with token ABI using bytes. {e!s}',
            )
            abi = self.contracts.univ1lp_abi
            contract = EvmContract(address=address, abi=abi, deployed_block=0)
            try:
                decoded = self._process_contract_info(
                    output=output,
                    properties=ERC20_PROPERTIES,
                    contract=contract,
                    token_kind=TokenKind.ERC20,
                )
            except (OverflowError, DecodingError) as err:
                # if even the bytes abi fails, this definitely isn't a valid erc20 token
                raise NotERC20Conformant from err

            log.debug(f'{address} was successfully decoded as ERC20 token')

        for prop, value in zip_longest(ERC20_PROPERTIES, decoded):
            if isinstance(value, bytes):
                value = value.rstrip(b'\x00').decode()  # noqa: PLW2901
            info[prop] = value

        return info

    def _query_token_contract(
            self,
            abi: ABI,
            properties: tuple[str, ...],
            address: ChecksumEvmAddress,
    ) -> list[tuple[bool, bytes]]:
        contract = EvmContract(address=address, abi=abi, deployed_block=0)
        try:
            # Output contains call status and result
            output = self.multicall_2(
                require_success=False,
                calls=[(address, contract.encode(method_name=prop)) for prop in properties],
            )
        except RemoteError:
            # If something happens in the connection the output should have
            # the same length as the tuple of properties
            output = [(False, b'')] * len(properties)

        return output

    def get_erc20_contract_info(self, address: ChecksumEvmAddress) -> dict[str, Any]:
        """
        Query an erc20 contract address and return basic information as:
        - Decimals
        - name
        - symbol
        At all times, the dictionary returned contains the keys; decimals, name & symbol.
        Although the values might be None.
        if it is provided in the contract. This method may raise:
        - BadFunctionCallOutput: If there is an error calling a bad address
        - NotERC20Conformant
        """
        if (cache := self.contract_info_erc20_cache.get(address)) is not None:
            return cache

        output = self._query_token_contract(abi=self.contracts.erc20_abi, properties=ERC20_PROPERTIES, address=address)  # noqa: E501
        info = self._process_and_create_erc20_info(
            output=output,
            address=address,
        )
        self.contract_info_erc20_cache.add(address, info)
        return info

    def get_erc721_contract_info(self, address: ChecksumEvmAddress) -> dict[str, Any]:
        """
        Query an erc721 contract address and return basic information.
        - name
        - symbol
        At all times, the dictionary returned contains the keys; name & symbol.
        Although the values might be None. https://eips.ethereum.org/EIPS/eip-721
        According to the standard both name and symbol are optional.
        if it is provided in the contract. This method may raise:
        - BadFunctionCallOutput: If there is an error calling a bad address
        - NotERC721Conformant: If the address can't be decoded as an ERC721 contract
        """
        if (cache := self.contract_info_erc721_cache.get(address)) is not None:
            return cache

        output = self._query_token_contract(abi=self.contracts.erc721_abi, properties=ERC721_PROPERTIES, address=address)  # noqa: E501

        try:
            decoded = self._process_contract_info(
                output=output,
                properties=ERC721_PROPERTIES,
                contract=EvmContract(address=address, abi=self.contracts.erc721_abi, deployed_block=0),  # noqa: E501
                token_kind=TokenKind.ERC721,
            )
        except (OverflowError, DecodingError) as e:
            raise NotERC721Conformant(f'{address} token does not conform to the ERC721 spec') from e  # noqa: E501

        info: dict[str, Any] = {}
        for prop, value in zip_longest(ERC721_PROPERTIES, decoded):
            if isinstance(value, bytes):
                value = value.rstrip(b'\x00').decode()  # noqa: PLW2901
            info[prop] = value

        self.contract_info_erc721_cache.add(address, info)
        return info

    def _process_contract_info(
            self,
            output: list[tuple[bool, bytes]],
            properties: tuple[str, ...],
            contract: EvmContract,
            token_kind: TokenKind,
    ) -> list[int | (str | bytes) | None]:
        """Decodes information i.e. (decimals, symbol, name) about the token contract.
        - `decimals` property defaults to 18.
        - `name` and `symbol` default to None.
        May raise:
        - OverflowError
        - InsufficientDataBytes (subclass of eth_abi.exceptions.DecodingError)
        - InvalidPointer (subclass of eth_abi.exceptions.DecodingError)
        """
        decoded_contract_info = []
        for method_name, method_value in zip(properties, output, strict=True):
            if method_value[0] is True and len(method_value[1]) != 0:
                decoded_contract_info.append(contract.decode(method_value[1], method_name)[0])
                continue

            if token_kind == TokenKind.ERC20:
                # for missing erc20 methods, use default decimals for decimals or None for others
                if method_name == 'decimals':
                    decoded_contract_info.append(DEFAULT_TOKEN_DECIMALS)
                else:
                    decoded_contract_info.append(None)
            else:  # for all others default to None
                decoded_contract_info.append(None)

        return decoded_contract_info

    def get_contract_deployed_block(self, address: ChecksumEvmAddress) -> int | None:
        """Get the deployed block of a contract

        Returns None if the address is not a contract.

        May raise:
        - RemoteError: in case of a problem contacting chain/nodes/remotes"""
        if (deployed_hash := self.get_contract_creation_hash(
            chain_id=self.chain_id,
            address=address,
        )) is None:
            return None

        transaction, _ = self.get_transaction_by_hash(deployed_hash)
        return transaction.block_number

    def maybe_timestamp_to_block_range(
            self,
            period: TimestampOrBlockRange,
    ) -> TimestampOrBlockRange:
        if period.range_type == 'timestamps':
            return TimestampOrBlockRange(
                range_type='blocks',
                from_value=self.get_blocknumber_by_time(ts=Timestamp(period.from_value)),
                to_value=self.get_blocknumber_by_time(ts=Timestamp(period.to_value)),
            )

        return period  # no op for block ranges

    # -- methods to be implemented by child classes --

    def get_blocknumber_by_time(
            self,
            ts: Timestamp,
            closest: Literal['before', 'after'] = 'before',
    ) -> int:
        """Searches for the blocknumber of a specific timestamp, checking the cached values first
        and then querying the indexers, with blockscout first, then etherscan.
        May raise RemoteError if all indexers fail.
        """
        # check if value exists in the cache
        if (block_number := self.timestamp_to_block_cache[self.chain_id].get(ts)) is not None:
            return block_number

        block_number = self._try_indexers(
            func=lambda indexer: indexer.get_blocknumber_by_time(
                chain_id=self.chain_id,
                ts=ts,
                closest=closest,
            ),
        )
        self.timestamp_to_block_cache[self.chain_id].add(key=ts, value=block_number)
        return block_number

    def maybe_get_l1_fees(
            self,
            account: ChecksumEvmAddress,
            tx_hash: EVMTxHash,
            block_number: int,
    ) -> int | None:
        """Retrieve L1 fee data for L2 transactions from available indexers.

        Returns L1 fee in wei if successful, None if chain unsupported or query fails.
        """
        if self.chain_id not in L2_CHAINIDS_WITH_L1_FEES:
            return None

        try:
            return self._try_indexers(
                func=lambda indexer: indexer.get_l1_fee(
                    chain_id=self.chain_id,  # type: ignore[arg-type]  # mypy doesn't understand the check above
                    account=account,
                    tx_hash=tx_hash,
                    block_number=block_number,
                ),
            )
        except RemoteError as e:
            log.error(f'Failed to get L1 fees for {account=} {tx_hash=} {block_number=} due to {e!s}')  # noqa: E501
            return None

    # -- methods to be optionally implemented by child classes --

    def logquery_block_range(
            self,
            web3: Web3,  # pylint: disable=unused-argument
            contract_address: ChecksumEvmAddress,  # pylint: disable=unused-argument
    ) -> int:
        """
        May be optionally implemented by subclasses to set special rules on how to
        decide the block range for a specific logquery.
        """
        return WEB3_LOGQUERY_BLOCK_RANGE

    def _additional_receipt_processing(self, tx_receipt: dict[str, Any]) -> None:
        """Performs additional tx_receipt processing where necessary"""

    @protect_with_lock()
    def ensure_cache_data_is_updated(
            self,
            cache_type: CacheType,
            query_method: Callable,
            force_refresh: bool = False,
            chain_id: ChainID | None = None,
            cache_key_parts: Sequence[str] | None = None,
    ) -> RemoteDataQueryStatus:
        """
        It checks if the cache data is fresh enough and if not, it queries
        the remote sources of the data and stores it to the globaldb cache tables.
        Returns true if the cache was modified or false otherwise.

        If the query_method logic fails due to a RemoteError this function handles
        it and returns False. Other errors aren't handled in this function.

        - cache type: The cache type to check for freshness
        - query_method: The method that queries the remote source for the data
        - save_method: The method that saves the data to the cache tables
        - force_refresh: If True, the cache will be updated even if it is fresh, and limits will
          be ignored, refreshing all the cached data.
        - cache_key_parts: The parts to be used to check cache freshness along with cache_type
        """
        if cache_key_parts is None:
            cache_key_parts = []
        if (
            should_update_protocol_cache(self.database, cache_type, cache_key_parts) is False and
            force_refresh is False
        ):
            log.debug(f'Not refreshing cache {cache_type}. Queried recently')
            return RemoteDataQueryStatus.NO_UPDATE

        try:
            new_data = query_method(
                inquirer=self,
                cache_type=cache_type,
                msg_aggregator=self.database.msg_aggregator,
                reload_all=force_refresh,
            )
        except RemoteError as e:
            log.error(
                f'Failed to call {query_method} when updating cache {cache_type} due to {e}',
            )
            return RemoteDataQueryStatus.FAILED

        return (
            RemoteDataQueryStatus.NEW_DATA if new_data is not None
            else RemoteDataQueryStatus.NO_UPDATE
        )

    def is_safe_proxy_or_eoa(self, address: ChecksumEvmAddress) -> bool:
        """
        Check if an address is a SAFE contract or an EoA. We do this by checking the getThreshold,
        VERSION and getChainId methods. We assume that if a contract has the same methods as a
        safe then it is a safe. Also EoAs return (true, b'') for any method so this function
        will also return True.
        """
        if (tracked_value := self._known_accounts_cache.get(address)) is not None:
            # use a cache to avoid repeating the same query several times
            return tracked_value

        contract = EvmContract(address=address, abi=SAFE_BASIC_ABI)  # avoid creating the contract 3 times in the calls list  # noqa: E501
        calls = [
            (address, contract.encode(method_name=method_name, arguments=[]))
            for method_name in ('getThreshold', 'VERSION', 'getChainId')
        ]
        try:
            outputs = self.multicall_2(
                calls=calls,
                require_success=False,
            )
        except RemoteError as e:
            log.error(
                f'Failed to check SAFE properties for {address} in {self.chain_name} due to {e}. '
                'Skipping',
            )
            return False

        return all(result_tuple[0] for result_tuple in outputs)

    @overload
    def get_transactions(
            self,
            account: ChecksumEvmAddress | None,
            action: Literal['txlistinternal'],
            period_or_hash: TimestampOrBlockRange | EVMTxHash | None = None,
    ) -> Iterator[list[EvmInternalTransaction]]:
        ...

    @overload
    def get_transactions(
            self,
            account: ChecksumEvmAddress | None,
            action: Literal['txlist'],
            period_or_hash: TimestampOrBlockRange | EVMTxHash | None = None,
    ) -> Iterator[list[EvmTransaction]]:
        ...

    def get_transactions(
            self,
            account: ChecksumEvmAddress | None,
            action: Literal['txlist', 'txlistinternal'],
            period_or_hash: TimestampOrBlockRange | EVMTxHash | None = None,
    ) -> Iterator[list[EvmTransaction]] | Iterator[list[EvmInternalTransaction]]:
        """Returns an iterator of transaction lists for a given account, action, and period/hash.
        Tries etherscan first, then blockscout. Raises RemoteError if both fail.
        """
        yield from self._try_indexers_iterable(func=lambda indexer: indexer.get_transactions(  # type: ignore[misc]
            chain_id=self.chain_id,
            account=account,
            period_or_hash=period_or_hash,
            action=action,
        ))

    def get_token_transaction_hashes(
            self,
            account: ChecksumEvmAddress,
            from_block: int | None = None,
            to_block: int | None = None,
    ) -> Iterator[list[EVMTxHash]]:
        yield from self._try_indexers_iterable(func=lambda indexer: indexer.get_token_transaction_hashes(  # noqa: E501
            chain_id=self.chain_id,
            account=account,
            from_block=from_block,
            to_block=to_block,
        ))

    def has_activity(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress,
    ) -> HasChainActivity:
        return self._try_indexers(func=lambda indexer: indexer.has_activity(
            chain_id=chain_id,
            account=account,
        ))

    def get_contract_abi(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            address: ChecksumEvmAddress,
    ) -> str | None:
        return self._try_indexers(func=lambda indexer: indexer.get_contract_abi(
            chain_id=chain_id,
            address=address,
        ))

    def get_contract_creation_hash(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            address: ChecksumEvmAddress,
    ) -> EVMTxHash | None:
        return self._try_indexers(func=lambda indexer: indexer.get_contract_creation_hash(
            chain_id=chain_id,
            address=address,
        ))

    def _get_indexers_in_order(self) -> list[tuple[EvmIndexer, EtherscanLikeApi]]:
        """Return available indexers respecting user-defined order and optional subset."""
        return [
            (indexer_name, indexer)
            for indexer_name in CachedSettings().get_evm_indexers_order_for_chain(chain_id=self.chain_id)  # noqa: E501
            if (indexer := self.available_indexers.get(indexer_name)) is not None
        ]

    def _try_indexers(self, func: Callable[[EtherscanLikeApi], T]) -> T:
        """Tries to call the given function on the indexers in order until one succeeds.
        Raises RemoteError if all fail or NoAvailableIndexers if there are no indexers available.
        """
        if len(ordered_indexers := self._get_indexers_in_order()) == 0:
            raise NoAvailableIndexers(f'No indexers are available for {self.chain_name}')

        errors: list[tuple[str, Exception]] = []
        for indexer_name, indexer in ordered_indexers:
            if indexer_name not in self.available_indexers:
                continue  # was removed while looping

            try:
                return func(indexer)
            except ChainNotSupported as e:
                if self.available_indexers.pop(indexer_name, None) is not None:
                    log.warning(  # removed the indexer
                        f'Indexer {indexer.name} doesnt support {self.chain_name} with the given '
                        f'API key. {e!s} Removing it from the available indexers for this chain.',
                    )
                    errors.append((indexer.name, e))
            except RemoteError as e:
                log.warning(f'Failed to query {indexer.name} due to {e!s}. Trying next indexer.')
                errors.append((indexer.name, e))

        raise RemoteError(
            f'Failed to query any indexer. '
            f"Errors: {', '.join(f'{name}: {e!s}' for name, e in errors)}",
        )

    def _try_indexers_iterable(
            self,
            func: Callable[[EtherscanLikeApi], Iterator[T]],
    ) -> Iterator[T]:
        """Wrapper for _try_indexers that returns an iterator instead of a single value."""
        def _query_indexer_iterator(indexer: EtherscanLikeApi) -> Iterator[T]:
            """Consume the first item in the iterator returned by `func` so if it fails the
            exception is raised immediately, and _try_indexers goes to the next indexer.
            """
            generator = func(indexer)
            # Force execution for first item so we go to the next indexer if this one fails.
            first_batch = next(generator)
            return itertools.chain([first_batch], generator)

        yield from self._try_indexers(func=_query_indexer_iterator)


class EvmNodeInquirerWithProxies(EvmNodeInquirer):
    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: Etherscan,
            routescan: Routescan,
            blockchain: SUPPORTED_EVM_CHAINS_TYPE,
            contracts: EvmContracts,
            contract_scan: 'EvmContract',
            contract_multicall: 'EvmContract',
            dsproxy_registry: 'EvmContract',
            native_token: CryptoAsset,
            rpc_timeout: int = DEFAULT_RPC_TIMEOUT,
            blockscout: Blockscout | None = None,
    ) -> None:
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            routescan=routescan,
            blockchain=blockchain,
            contracts=contracts,
            contract_scan=contract_scan,
            contract_multicall=contract_multicall,
            rpc_timeout=rpc_timeout,
            native_token=native_token,
            blockscout=blockscout,
        )
        self.proxies_inquirer = EvmProxiesInquirer(
            node_inquirer=self,
            dsproxy_registry=dsproxy_registry,
        )


class DSProxyInquirerWithCacheData(EvmNodeInquirerWithProxies):
    """This is the inquirer that needs to be used by chains with modules (protocols)
    that store data in the cache tables of the globaldb. For example velodrome in
    optimism and curve in ethereum store data in cache tables."""

    def __init__(
            self,
            greenlet_manager: GreenletManager,
            database: 'DBHandler',
            etherscan: Etherscan,
            routescan: Routescan,
            blockchain: SUPPORTED_EVM_CHAINS_TYPE,
            contracts: EvmContracts,
            contract_scan: 'EvmContract',
            contract_multicall: 'EvmContract',
            dsproxy_registry: 'EvmContract',
            native_token: CryptoAsset,
            rpc_timeout: int = DEFAULT_RPC_TIMEOUT,
            blockscout: Blockscout | None = None,
    ) -> None:
        super().__init__(
            greenlet_manager=greenlet_manager,
            database=database,
            etherscan=etherscan,
            routescan=routescan,
            blockchain=blockchain,
            contracts=contracts,
            contract_scan=contract_scan,
            contract_multicall=contract_multicall,
            rpc_timeout=rpc_timeout,
            native_token=native_token,
            dsproxy_registry=dsproxy_registry,
            blockscout=blockscout,
        )
