import abc
import json
import logging
import operator
from abc import ABC
from collections.abc import Iterator
from enum import Enum, auto
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal, overload

import gevent
import requests
from requests import Response

from rotkehlchen.chain.evm.constants import GENESIS_HASH, ZERO_ADDRESS
from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2ChainIdsWithL1FeesType
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.constants import TX_DECODED
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalServiceWithApiKey
from rotkehlchen.externalapis.utils import get_earliest_ts
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_transaction,
    deserialize_int_from_str,
    deserialize_timestamp,
)
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    ApiKey,
    ChainID,
    ChecksumEvmAddress,
    EvmInternalTransaction,
    EvmTransaction,
    EVMTxHash,
    ExternalService,
    Location,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import set_user_agent
from rotkehlchen.utils.network import create_session
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

TRANSACTIONS_BATCH_NUM: Final = 10

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _hashes_tuple_to_list(hashes: set[tuple[EVMTxHash, Timestamp]]) -> list[EVMTxHash]:
    """Turns the set of hashes/timestamp to a timestamp ascending ordered list

    This function needs to exist since Set has no guaranteed order of iteration.
    """
    return [x[0] for x in sorted(hashes, key=operator.itemgetter(1))]


class HasChainActivity(Enum):
    """
    Classify the type of transaction first found in blockscout/etherscan.
    TRANSACTIONS means that the endpoint for transactions/internal transactions
    had entries, TOKENS means that the tokens endpoint had entries, BALANCE means
    that the address has a non-zero native asset balance and NONE means that no
    activity was found."""
    TRANSACTIONS = auto()
    TOKENS = auto()
    BALANCE = auto()
    NONE = auto()


class EtherscanLikeApi(ExternalServiceWithApiKey, ABC):
    """Base class for any APIs similar to etherscan."""

    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
            service_name: ExternalService,
            pagination_limit: int,
            default_api_key: ApiKey,
    ) -> None:
        super().__init__(database=database, service_name=service_name)
        self.msg_aggregator = msg_aggregator
        self.session = create_session()
        set_user_agent(self.session)
        self.default_api_key = default_api_key
        self.pagination_limit = pagination_limit
        self.name = service_name.name.capitalize()

    @staticmethod
    @abc.abstractmethod
    def _get_url(chain_id: SUPPORTED_CHAIN_IDS) -> str:
        """Get the API URL for the given chain. Override in subclasses for different endpoints.
        May raise UnsupportedChain if the service does not support the given chain.
        """

    @staticmethod
    @abc.abstractmethod
    def _build_query_params(
            module: str,
            action: str,
            api_key: ApiKey,
            chain_id: SUPPORTED_CHAIN_IDS,
    ) -> dict[str, str]:
        """Build parameters for API requests. Override in subclasses for different formats."""

    @abc.abstractmethod
    def get_l1_fee(
            self,
            chain_id: L2ChainIdsWithL1FeesType,
            account: ChecksumEvmAddress,
            tx_hash: EVMTxHash,
            block_number: int,
    ) -> int:
        """Attempt to get the L1 fee for the given transaction.
        Returns the L1 fee or raises RemoteError if the fee cannot be retrieved.
        """

    def _handle_rate_limit(
            self,
            response: Response,
            current_backoff: int,
            backoff_limit: int,
            chain_id: ChainID,
    ) -> int:
        """Handles rate limiting errors from etherscan-like services. May be overridden in
        subclasses to handle anything special from a given service. Returns the new backoff time.
        May raise RemoteError if the rate limit is exceeded even after backing off.
        """
        if current_backoff >= backoff_limit:
            raise RemoteError(
                f'Getting {self.name} too many requests error '
                f'even after we incrementally backed off while querying {chain_id}',
            )

        log.debug(
            f'Got too many requests error from {chain_id} {self.name}. Will '
            f'backoff for {current_backoff} seconds.',
        )
        gevent.sleep(current_backoff)
        return current_backoff * 2

    def _additional_json_response_handling(
            self,
            action: str,
            chain_id: ChainID,
            response: Response,
            json_ret: dict[str, Any],
            result: str,
            current_backoff: int,
    ) -> int | bool | list | None:
        """Overridden in subclasses to handle any additional checks that need to be done on json
        responses.

        Possible return values and how they are handled:
        - False: No special handling needed. The result is valid and can be returned.
        - int: Rate limited response. Will retry.
        - list or None: This value will be returned directly.

        May raise RemoteError or ChainNotSupported if the result indicates an error.
        """
        return False  # no-op by default

    @overload
    def _query(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            module: str,
            action: Literal[
                'balancemulti',
                'txlist',
                'txlistinternal',
                'tokentx',
                'getLogs',
                'txsBeaconWithdrawal',
            ],
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> list[dict[str, Any]]:
        ...

    @overload
    def _query(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            module: str,
            action: Literal[
                'eth_getTransactionReceipt',
                'eth_getTransactionByHash',
            ],
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> dict[str, Any] | None:
        ...

    @overload
    def _query(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            module: str,
            action: Literal[
                'getcontractcreation',
            ],
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> list[dict[str, Any]] | None:
        ...

    @overload
    def _query(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            module: str,
            action: Literal[
                'getabi',
            ],
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> str | None:
        ...

    @overload
    def _query(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            module: str,
            action: Literal[
                'eth_getBlockByNumber',
            ],
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> dict[str, Any]:
        ...

    @overload
    def _query(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            module: str,
            action: Literal[
                'balance',
                'tokenbalance',
                'eth_blockNumber',
                'eth_getCode',
                'eth_call',
                'getblocknobytime',
            ],
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> str:
        ...

    def _query(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            module: str,
            action: str,
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> list[dict[str, Any]] | str | int | dict[str, Any] | None:
        """Queries etherscan-like service

        None is a valid result for this function when the requested information doesn't exist.
        Happens when asking for the code of a contract, transaction by hash, receipt...

        May raise:
        - RemoteError if there are any problems with reaching the service or if
        an unexpected response is returned. Also in the case of exhausting the backoff time.
        """
        result = None
        if (api_key := self._get_api_key()) is None and self.default_api_key is not None:
            api_key = self.default_api_key
            log.debug(f'Using default {self.name} key')

        params = self._build_query_params(
            module=module,
            action=action,
            api_key=api_key,
            chain_id=chain_id,
        )
        if options:
            params.update(options)

        backoff = 1
        cached_settings = CachedSettings()
        timeout = timeout or cached_settings.get_timeout_tuple()
        backoff_limit = cached_settings.get_query_retry_limit()
        api_url = self._get_url(chain_id=chain_id)
        response = None
        while backoff < backoff_limit:
            log.debug(f'Querying {self.name} for {chain_id}: {api_url} with params: {params}')
            try:
                response = self.session.get(url=api_url, params=params, timeout=timeout)
            except requests.exceptions.RequestException as e:
                raise RemoteError(f'{self.name} API request failed due to {e!s}') from e

            if response.status_code == HTTPStatus.TOO_MANY_REQUESTS:
                backoff = self._handle_rate_limit(
                    response=response,
                    current_backoff=backoff,
                    backoff_limit=backoff_limit,
                    chain_id=chain_id,
                )
                continue
            elif response.status_code != 200:
                raise RemoteError(
                    f'{self.name} API request {response.url} failed '
                    f'with HTTP status code {response.status_code} and text '
                    f'{response.text}',
                )

            try:
                json_ret = jsonloads_dict(response.text)
            except JSONDecodeError as e:
                raise RemoteError(
                    f'{self.name} API request {response.url} returned invalid '
                    f'JSON response: {response.text}',
                ) from e

            try:
                if (result := json_ret.get('result')) is None:
                    if action in {'eth_getTransactionByHash', 'eth_getTransactionReceipt', 'getcontractcreation'}:  # noqa: E501
                        return None

                    raise RemoteError(
                        f'Unexpected format of {self.name} response for request {response.url}. '
                        f'Missing a result in response. Response was: {response.text}',
                    )

                handling_response = self._additional_json_response_handling(
                    action=action,
                    chain_id=chain_id,
                    response=response,
                    json_ret=json_ret,
                    result=result,
                    current_backoff=backoff,
                )
                if handling_response is not False:
                    if isinstance(handling_response, int):  # rate limited response
                        backoff = handling_response
                        continue

                    return handling_response

            except KeyError as e:
                raise RemoteError(
                    f'Unexpected format of {chain_id} {self.name} response for request {response.url}. '  # noqa: E501
                    f'Missing key entry for {e!s}. Response was: {response.text}',
                ) from e

            # success, break out of the loop and return result
            return result

        # will only run if we get out of the loop due to backoff limit
        assert response is not None, 'This loop always runs at least once and response is not None'
        msg = (
            f'{chain_id.name.capitalize()} {self.name} API request to {response.url} failed '
            f'due to backing off longer than the max backoff of {backoff_limit} seconds.'
        )
        log.error(msg)
        raise RemoteError(msg)

    def _process_timestamp_or_blockrange(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            period: TimestampOrBlockRange,
            options: dict[str, Any],
    ) -> dict[str, Any]:
        """Process TimestampOrBlockRange and populate call options"""
        if period.range_type == 'blocks':
            from_block = period.from_value
            to_block = period.to_value
        else:  # timestamps
            from_block = self.get_blocknumber_by_time(
                chain_id=chain_id,
                ts=period.from_value,  # type: ignore
                closest='before',
            )
            to_block = self.get_blocknumber_by_time(
                chain_id=chain_id,
                ts=period.to_value,  # type: ignore
                closest='before',
            )

        options['startblock'] = str(from_block)
        options['endblock'] = str(to_block)
        return options

    def _maybe_paginate(
            self,
            result: list[dict[str, Any]],
            options: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Check if the results have hit the pagination limit.
        If yes adjust the options accordingly. Otherwise signal we are done"""
        if len(result) != self.pagination_limit:
            return None

        # else we hit the limit. Query once more with startblock being the last
        # block we got. There may be duplicate entries if there are more than one
        # entries for that last block but they should be filtered
        # out when we input all of these in the DB
        last_block = result[-1]['blockNumber']
        options['startblock'] = last_block
        return options

    @overload
    def get_transactions(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress | None,
            action: Literal['txlistinternal'],
            period_or_hash: TimestampOrBlockRange | EVMTxHash | None = None,
    ) -> Iterator[list[EvmInternalTransaction]]:
        ...

    @overload
    def get_transactions(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress | None,
            action: Literal['txlist'],
            period_or_hash: TimestampOrBlockRange | EVMTxHash | None = None,
    ) -> Iterator[list[EvmTransaction]]:
        ...

    def get_transactions(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress | None,
            action: Literal['txlist', 'txlistinternal'],
            period_or_hash: TimestampOrBlockRange | EVMTxHash | None = None,
    ) -> Iterator[list[EvmTransaction]] | Iterator[list[EvmInternalTransaction]]:
        """Gets a list of transactions (either normal or internal) for an account.

        Can specify a given timestamp or block period.

        For internal transactions can also query by parent transaction hash instead
        Also the account is optional in case of internal transactions.

        May raise:
        - RemoteError due to self._query(). Also if the returned result
        is not in the expected format
        """
        options = {'sort': 'asc'}
        parent_tx_hash = None
        if account:
            options['address'] = str(account)
        if period_or_hash is not None:
            if isinstance(period_or_hash, TimestampOrBlockRange):
                options = self._process_timestamp_or_blockrange(
                    chain_id=chain_id,
                    period=period_or_hash,
                    options=options,
                )
            else:  # has to be parent transaction hash and internal transaction
                options['txhash'] = period_or_hash.hex()
                parent_tx_hash = period_or_hash

        transactions: list[EvmTransaction] | list[EvmInternalTransaction] = []
        is_internal = action == 'txlistinternal'

        while True:
            if len(result := self._query(
                chain_id=chain_id,
                module='account',
                action=action,
                options=options,
            )) == 0:
                log.debug(
                    f'Length of account {action} result on {chain_id.name} '
                    f'from {self.name} is 0. Breaking out of the query',
                )
                break

            last_ts = deserialize_timestamp(result[0]['timeStamp'])
            for entry in result:
                try:  # Handle normal transactions. Internal dict does not contain a hash sometimes
                    if is_internal or entry['hash'].startswith('GENESIS') is False:
                        tx, _ = deserialize_evm_transaction(  # type: ignore
                            data=entry,
                            internal=is_internal,
                            chain_id=chain_id,
                            evm_inquirer=None,
                            parent_tx_hash=parent_tx_hash,
                        )
                    else:  # Handling genesis transactions
                        assert self.db is not None, 'self.db should exists at this point'
                        dbtx = DBEvmTx(self.db)
                        tx = dbtx.get_or_create_genesis_transaction(
                            account=account,  # type: ignore[arg-type]  # always exists here
                            chain_id=chain_id,
                        )
                        trace_id = dbtx.get_max_genesis_trace_id(chain_id)
                        entry['from'] = ZERO_ADDRESS
                        entry['hash'] = GENESIS_HASH
                        entry['traceId'] = trace_id
                        internal_tx, _ = deserialize_evm_transaction(
                            data=entry,
                            internal=True,
                            chain_id=chain_id,
                            evm_inquirer=None,
                        )
                        with self.db.user_write() as cursor:
                            dbtx.add_evm_internal_transactions(
                                write_cursor=cursor,
                                transactions=[internal_tx],
                                relevant_address=None,  # can't know the address here
                            )

                        dbevents = DBHistoryEvents(self.db)
                        with self.db.user_write() as write_cursor:
                            # Delete decoded genesis events so they can be later redecoded.
                            dbevents.delete_events_by_tx_ref(
                                write_cursor=write_cursor,
                                tx_refs=[GENESIS_HASH],
                                location=Location.from_chain_id(chain_id.to_blockchain()),  # type: ignore
                            )
                            write_cursor.execute(
                                'DELETE from evm_tx_mappings WHERE tx_id=(SELECT identifier FROM '
                                'evm_transactions WHERE tx_hash=? AND chain_id=?) AND value=?',
                                (GENESIS_HASH, chain_id.serialize_for_db(), TX_DECODED),
                            )
                except DeserializationError as e:
                    self.msg_aggregator.add_warning(f'{e!s}. Skipping transaction')
                    continue

                timestamp = deserialize_timestamp(entry['timeStamp'])
                if timestamp > last_ts and len(transactions) >= TRANSACTIONS_BATCH_NUM:
                    yield transactions
                    last_ts = timestamp
                    transactions = []
                transactions.append(tx)

            if (new_options := self._maybe_paginate(result=result, options=options)) is None:
                break  # no need to paginate further
            options = new_options

        yield transactions

    def get_token_transaction_hashes(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress,
            from_block: int | None = None,
            to_block: int | None = None,
    ) -> Iterator[list[EVMTxHash]]:
        options = {'address': str(account), 'sort': 'asc'}
        if from_block is not None:
            options['startblock'] = str(from_block)
        if to_block is not None:
            options['endblock'] = str(to_block)

        hashes: set[tuple[EVMTxHash, Timestamp]] = set()
        while True:
            result = self._query(
                chain_id=chain_id,
                module='account',
                action='tokentx',
                options=options,
            )
            last_ts = deserialize_timestamp(result[0]['timeStamp']) if (result and len(result) != 0) else None  # noqa: E501
            for entry in result:
                try:
                    timestamp = deserialize_timestamp(entry['timeStamp'])
                except DeserializationError as e:
                    log.error(
                        f"Failed to read transaction timestamp {entry['hash']} from {chain_id} "
                        f'{self.name} for {account} in the range {from_block} to {to_block}. {e!s}',  # noqa: E501
                    )
                    continue

                if timestamp > last_ts and len(hashes) >= TRANSACTIONS_BATCH_NUM:  # type: ignore
                    yield _hashes_tuple_to_list(hashes)
                    hashes = set()
                    last_ts = timestamp
                try:
                    hashes.add((deserialize_evm_tx_hash(entry['hash']), timestamp))
                except DeserializationError as e:
                    log.error(
                        f"Failed to read transaction hash {entry['hash']} from {chain_id} "
                        f'{self.name} for {account} in the range {from_block} to {to_block}. {e!s}',  # noqa: E501
                    )
                    continue

            if (new_options := self._maybe_paginate(result=result, options=options)) is None:
                break  # no need to paginate further
            options = new_options

        yield _hashes_tuple_to_list(hashes)

    def get_blocknumber_by_time(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            ts: Timestamp,
            closest: Literal['before', 'after'] = 'before',
    ) -> int:
        """Performs the etherscan like api call to get the blocknumber by a specific timestamp

        May raise:
        - RemoteError if there are any problems with reaching the service or if
        an unexpected response is returned
        """
        # set per-chain earliest timestamps that can be turned to blocks. Never returns block 0
        if ts < get_earliest_ts(chain_id):
            return 0  # etherscan does not handle timestamps close to genesis well

        options = {'timestamp': ts, 'closest': closest}
        result = self._query(
            chain_id=chain_id,
            module='block',
            action='getblocknobytime',
            options=options,
        )
        try:
            number = deserialize_int_from_str(result, f'{self.name} getblocknobytime')
        except DeserializationError as e:
            raise RemoteError(
                f'Could not read blocknumber from {self.name} for {chain_id}  '
                f'getblocknobytime result {result}',
            ) from e

        return number

    def has_activity(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            account: ChecksumEvmAddress,
    ) -> HasChainActivity:
        """Queries native asset balance, transactions, internal_txs and tokentx for an address
        with limit=1 just to quickly determine if the account has had any activity in the chain.
        We make a distinction between transactions and ERC20 transfers since ERC20
        are often spammed. If there was no activity at all we return the enum value
        NONE.
        """
        options = {'address': str(account), 'page': 1, 'offset': 1}
        result = self._query(chain_id=chain_id, module='account', action='txlist', options=options)
        if len(result) != 0:
            return HasChainActivity.TRANSACTIONS
        result = self._query(chain_id=chain_id, module='account', action='txlistinternal', options=options)  # noqa: E501
        if len(result) != 0:
            return HasChainActivity.TRANSACTIONS
        result = self._query(chain_id=chain_id, module='account', action='tokentx', options=options)  # noqa: E501
        if len(result) != 0:
            return HasChainActivity.TOKENS
        if chain_id in {ChainID.ETHEREUM, ChainID.GNOSIS}:
            balance = self._query(
                chain_id=chain_id,
                module='account',
                action='balance',
                options={'address': account},
            )
            if int(balance) != 0:
                return HasChainActivity.BALANCE
        return HasChainActivity.NONE

    def get_contract_abi(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            address: ChecksumEvmAddress,
    ) -> str | None:
        """Get the contract abi for the given address if verified.
        Returns `None` if the address is not a verified contract.
        May raise RemoteError if the query to the indexer fails.
        """
        if (result := self._query(
            chain_id=chain_id,
            module='contract',
            action='getabi',
            options={'address': address},
        )) is None:
            return None

        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return None

    def get_contract_creation_hash(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            address: ChecksumEvmAddress,
    ) -> EVMTxHash | None:
        """Get the contract creation tx hash for the given address.
        Returns None if the address is not a contract.
        May raise RemoteError in case of problems contacting the indexer.
        """
        if (result := self._query(
            chain_id=chain_id,
            module='contract',
            action='getcontractcreation',
            options={'contractaddresses': address},
        )) is None:
            return None

        try:
            return deserialize_evm_tx_hash(result[0]['txHash'])
        except (DeserializationError, IndexError, KeyError) as e:
            msg = f'missing key {e!s}' if isinstance(e, KeyError) else f'{e!s}'
            log.error(f'Failed to get contract creation hash for {address} from {self.name}: {msg}')  # noqa: E501
            return None
