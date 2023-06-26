from collections.abc import Iterator
from typing import TYPE_CHECKING, Literal, Optional, Union

from rotkehlchen.chain.evm.constants import GENESIS_HASH, ZERO_ADDRESS
from rotkehlchen.chain.optimism.types import OptimismTransaction
from rotkehlchen.chain.structures import TimestampOrBlockRange
from rotkehlchen.db.constants import HISTORY_MAPPING_STATE_DECODED
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.etherscan import Etherscan
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_transaction,
    deserialize_timestamp,
)
from rotkehlchen.types import (
    ChecksumEvmAddress,
    EvmInternalTransaction,
    EvmTransaction,
    EVMTxHash,
    ExternalService,
    SupportedBlockchain,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.user_messages import MessagesAggregator

ETHERSCAN_TX_QUERY_LIMIT = 10000
TRANSACTIONS_BATCH_NUM = 10

class OptimismEtherscan(Etherscan):

    def __init__(
            self,
            database: 'DBHandler',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            database=database,
            msg_aggregator=msg_aggregator,
            chain=SupportedBlockchain.OPTIMISM,
            base_url='optimistic.etherscan.io',
            service=ExternalService.OPTIMISM_ETHERSCAN,
        )

    def get_transactions(
            self,
            account: Optional[ChecksumEvmAddress],
            action: Literal['txlist', 'txlistinternal'],
            period_or_hash: Optional[Union[TimestampOrBlockRange, EVMTxHash]] = None,
    ) -> Union[Iterator[list[OptimismTransaction]], Iterator[list[EvmInternalTransaction]]]:
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
                if period_or_hash.range_type == 'blocks':
                    from_block = period_or_hash.from_value
                    to_block = period_or_hash.to_value
                else:  # timestamps
                    from_block = self.get_blocknumber_by_time(
                        ts=period_or_hash.from_value,  # type: ignore
                        closest='before',
                    )
                    to_block = self.get_blocknumber_by_time(
                        ts=period_or_hash.to_value,  # type: ignore
                        closest='before',
                    )

                options['startBlock'] = str(from_block)
                options['endBlock'] = str(to_block)

            else:  # has to be parent transaction hash and internal transaction
                options['txHash'] = period_or_hash.hex()
                parent_tx_hash = period_or_hash

        transactions: Union[list[EvmTransaction], list[EvmInternalTransaction]] = []  # type: ignore  # noqa: E501
        is_internal = action == 'txlistinternal'
        chain_id = self.chain.to_chain_id()
        while True:
            result = self._query(module='account', action=action, options=options)
            last_ts = deserialize_timestamp(result[0]['timeStamp']) if len(result) != 0 else None
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
                        if type(tx) != EvmInternalTransaction:
                            tx_receipt = self.get_transaction_receipt(tx.tx_hash)
                            tx = OptimismTransaction(
                                tx_hash=tx.tx_hash,
                                chain_id=tx.chain_id,
                                timestamp=tx.timestamp,
                                block_number=tx.block_number,
                                from_address=tx.from_address,
                                to_address=tx.to_address,
                                value=tx.value,
                                gas=tx.gas,
                                gas_price=tx.gas_price,
                                gas_used=tx.gas_used,
                                input_data=tx.input_data,
                                nonce=tx.nonce,
                                l1_fee=int(tx_receipt['l1Fee'], 16),
                            )
                    else:  # Handling genesis transactions
                        assert self.db is not None, 'self.db should exists at this point'
                        dbtx = DBEvmTx(self.db)
                        tx = dbtx.get_or_create_genesis_transaction(
                            account=account,  # type: ignore[arg-type]  # always exists here
                            chain_id=chain_id,  # type: ignore[arg-type]  # is only supported chain
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
                            dbevents.delete_events_by_tx_hash(
                                write_cursor=write_cursor,
                                tx_hashes=[GENESIS_HASH],
                                chain_id=self.chain.to_chain_id(),  # type: ignore[arg-type]
                            )
                            write_cursor.execute(
                                'DELETE from evm_tx_mappings WHERE tx_hash=? AND chain_id=? AND value=?',  # noqa: E501
                                (GENESIS_HASH, self.chain.to_chain_id().serialize_for_db(), HISTORY_MAPPING_STATE_DECODED),  # noqa: E501
                            )
                except DeserializationError as e:
                    self.msg_aggregator.add_warning(f'{e!s}. Skipping transaction')
                    continue

                if tx.timestamp > last_ts and len(transactions) >= TRANSACTIONS_BATCH_NUM:
                    yield transactions
                    last_ts = tx.timestamp
                    transactions = []  # type: ignore
                transactions.append(tx)

            if len(result) != ETHERSCAN_TX_QUERY_LIMIT:
                break
            # else we hit the limit. Query once more with startBlock being the last
            # block we got. There may be duplicate entries if there are more than one
            # transactions for that last block but they should be filtered
            # out when we input all of these in the DB
            last_block = result[-1]['blockNumber']
            options['startBlock'] = last_block

        yield transactions
