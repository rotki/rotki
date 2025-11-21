import json
import logging
import operator
from abc import ABC, abstractmethod
from collections.abc import Iterator
from enum import Enum, auto
from http import HTTPStatus
from json.decoder import JSONDecodeError
from typing import TYPE_CHECKING, Any, Final, Literal, overload

import gevent
import requests
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.chain.evm.constants import GENESIS_HASH, ZERO_ADDRESS
from rotkehlchen.chain.evm.l2_with_l1_fees.types import L2ChainIdsWithL1FeesType
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.constants import TX_DECODED
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.interface import ExternalServiceWithRecommendedApiKey
from rotkehlchen.externalapis.utils import get_earliest_ts
from rotkehlchen.history.events.structures.eth2 import EthWithdrawalEvent
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_transaction,
    deserialize_fval,
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
from rotkehlchen.utils.misc import from_gwei, hexstr_to_int, set_user_agent, ts_sec_to_ms
from rotkehlchen.utils.network import create_session
from rotkehlchen.utils.serialization import jsonloads_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

ETHERSCAN_QUERY_LIMIT = 10000
TRANSACTIONS_BATCH_NUM = 10

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _hashes_tuple_to_list(hashes: set[tuple[EVMTxHash, Timestamp]]) -> list[EVMTxHash]:
    """Turns the set of hashes/timestamp to a timestamp ascending ordered list

    This function needs to exist since Set has no guaranteed order of iteration.
    """
    return [x[0] for x in sorted(hashes, key=operator.itemgetter(1))]


class EtherscanLikeApi(ABC):
    """Base class for any APIs similar to etherscan."""

    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        self.db = database
        self.msg_aggregator = msg_aggregator

    @abstractmethod
    def _query(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            module: str,
            action: str,
            options: dict[str, Any] | None = None,
            timeout: tuple[int, int] | None = None,
    ) -> list[dict[str, Any]] | (str | (list[EvmTransaction] | (dict[str, Any] | None))):
        ...

    @abstractmethod
    def get_blocknumber_by_time(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            ts: Timestamp,
            closest: Literal['before', 'after'] = 'before',
    ) -> int:
        ...

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

    @staticmethod
    def _maybe_paginate(
            result: list[dict[str, Any]],
            options: dict[str, Any],
    ) -> dict[str, Any] | None:  # noqa: E501
        """Check if the results have hit the pagination limit.
        If yes adjust the options accordingly. Otherwise signal we are done"""
        if len(result) != ETHERSCAN_QUERY_LIMIT:
            return None

        # else we hit the limit. Query once more with startBlock being the last
        # block we got. There may be duplicate entries if there are more than one
        # entries for that last block but they should be filtered
        # out when we input all of these in the DB
        last_block = result[-1]['blockNumber']
        options['startBlock'] = last_block
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
            result = self._query(
                chain_id=chain_id,
                module='account',
                action=action,
                options=options,
            )
            if len(result) == 0:
                log.debug('Length of account result is 0. Breaking out of the query')
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
                        f'etherscan for {account} in the range {from_block} to {to_block}. {e!s}',
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
                        f'etherscan for {account} in the range {from_block} to {to_block}. {e!s}',
                    )
                    continue

            if (new_options := self._maybe_paginate(result=result, options=options)) is None:
                break  # no need to paginate further
            options = new_options

        yield _hashes_tuple_to_list(hashes)
