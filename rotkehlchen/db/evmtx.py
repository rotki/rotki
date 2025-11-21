import logging
from typing import TYPE_CHECKING, Any, ClassVar, get_args

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.chain.arbitrum_one.constants import ARBITRUM_ONE_GENESIS
from rotkehlchen.chain.base.constants import BASE_GENESIS
from rotkehlchen.chain.binance_sc.constants import BINANCE_SC_GENESIS
from rotkehlchen.chain.ethereum.constants import ETHEREUM_GENESIS
from rotkehlchen.chain.ethereum.modules.eth2.constants import (
    CONSOLIDATION_REQUEST_CONTRACT,
    WITHDRAWAL_REQUEST_CONTRACT,
)
from rotkehlchen.chain.evm.constants import GENESIS_HASH, ZERO_ADDRESS
from rotkehlchen.chain.evm.structures import EvmTxReceipt, EvmTxReceiptLog
from rotkehlchen.chain.evm.types import EvmAccount
from rotkehlchen.chain.gnosis.constants import GNOSIS_GENESIS
from rotkehlchen.chain.optimism.constants import OPTIMISM_GENESIS
from rotkehlchen.chain.polygon_pos.constants import POLYGON_POS_GENESIS
from rotkehlchen.chain.scroll.constants import SCROLL_GENESIS
from rotkehlchen.db.constants import (
    EXTRAINTERNALTXPREFIX,
    TX_DECODED,
    TX_SPAM,
)
from rotkehlchen.db.dbtx import DBCommonTx
from rotkehlchen.db.filtering import (
    EvmTransactionsFilterQuery,
    EvmTransactionsNotDecodedFilterQuery,
)
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import (
    deserialize_evm_address,
    deserialize_int_from_hex_or_int,
    deserialize_timestamp,
)
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    SUPPORTED_EVM_CHAINS_TYPE,
    ChainID,
    ChecksumEvmAddress,
    EvmInternalTransaction,
    EvmTransaction,
    EvmTransactionAuthorization,
    EVMTxHash,
    Location,
    SupportedBlockchain,
    Timestamp,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.hexbytes import hexstring_to_bytes

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.gevent import DBCursor


class DBEvmTx(DBCommonTx[ChecksumEvmAddress, EvmTransaction, EVMTxHash, EvmTransactionsFilterQuery, EvmTransactionsNotDecodedFilterQuery]):  # noqa: E501
    # Index in the SQL result tuple where authorization fields (nonce, delegated_address) begin  # noqa: E501
    AUTHORIZATION_DATA_START_INDEX: ClassVar[int] = 13

    def add_transactions(
            self,
            write_cursor: 'DBCursor',
            evm_transactions: list[EvmTransaction],
            relevant_address: ChecksumEvmAddress | None,
    ) -> None:
        """Adds evm transactions to the database"""
        query = """
            INSERT OR IGNORE INTO evm_transactions(
              tx_hash,
              chain_id,
              timestamp,
              block_number,
              from_address,
              to_address,
              value,
              gas,
              gas_price,
              gas_used,
              input_data,
              nonce)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        for tx in evm_transactions:
            if (row_id := self.db.write_single_tuple(
                write_cursor=write_cursor,
                tuple_type='evm_transaction',
                query=query,
                entry=(
                    tx.tx_hash,
                    tx.chain_id.serialize_for_db(),
                    tx.timestamp,
                    tx.block_number,
                    tx.from_address,
                    tx.to_address,
                    str(tx.value),
                    str(tx.gas),
                    str(tx.gas_price),
                    str(tx.gas_used),
                    tx.input_data,
                    tx.nonce,
                ),
                relevant_address=relevant_address,
            )) is not None and tx.authorization_list is not None:
                self.db.write_tuples(
                    write_cursor=write_cursor,
                    tuple_type='evm_transactions_authorization',
                    query='INSERT OR IGNORE INTO evm_transactions_authorizations(tx_id, nonce, delegated_address) VALUES (?, ?, ?)',  # noqa: E501
                    tuples=[
                        (row_id, entry.nonce, entry.delegated_address)
                        for entry in tx.authorization_list
                    ],
                )

    def add_evm_internal_transactions(
            self,
            write_cursor: 'DBCursor',
            transactions: list[EvmInternalTransaction],
            relevant_address: ChecksumEvmAddress | None,
    ) -> None:
        """Adds evm internal transactions to the database"""
        tx_tuples = [(
            tx.trace_id,
            tx.from_address,
            tx.to_address,
            str(tx.value),
            str(tx.gas),
            str(tx.gas_used),
            tx.parent_tx_hash,
            tx.chain_id.serialize_for_db(),
        ) for tx in transactions]
        query = """
            INSERT OR IGNORE INTO evm_internal_transactions(
              parent_tx,
              trace_id,
              from_address,
              to_address,
              value,
              gas,
              gas_used
        ) SELECT evm_transactions.identifier, ?, ?, ?, ?, ?, ? FROM evm_transactions
            WHERE tx_hash=? AND chain_id=?
        """
        self.db.write_tuples(
            write_cursor=write_cursor,
            tuple_type='evm_internal_transaction',
            query=query,
            tuples=tx_tuples,
            relevant_address=relevant_address,
        )

    def get_evm_internal_transactions(
            self,
            parent_tx_hash: EVMTxHash,
            blockchain: SupportedBlockchain,
            from_address: ChecksumEvmAddress | None = None,
            to_address: ChecksumEvmAddress | None = None,
    ) -> list[EvmInternalTransaction]:
        """Get all internal transactions under a parent tx_hash for a given chain"""
        chain_id = blockchain.to_chain_id()
        address_filter, bindings = '', [parent_tx_hash, chain_id.serialize_for_db()]
        if from_address is not None:
            address_filter += ' AND ITX.from_address=?'
            bindings.append(from_address)
        if to_address is not None:
            address_filter += ' AND ITX.to_address=?'
            bindings.append(to_address)

        with self.db.conn.read_ctx() as cursor:
            results = cursor.execute(
                'SELECT ITX.trace_id, ITX.from_address, ITX.to_address, ITX.value, ITX.gas, '
                'ITX.gas_used FROM evm_internal_transactions ITX INNER JOIN evm_transactions TX '
                'ON ITX.parent_tx=TX.identifier WHERE TX.tx_hash=? AND TX.chain_id=?'
                f'{address_filter}', bindings,
            )
            transactions = []
            for result in results:
                tx = EvmInternalTransaction(
                    parent_tx_hash=parent_tx_hash,
                    chain_id=chain_id,
                    trace_id=result[0],
                    from_address=result[1],
                    to_address=result[2],
                    value=int(result[3]),
                    gas=int(result[4]),
                    gas_used=int(result[5]),
                )
                transactions.append(tx)

        return transactions

    def get_transactions(
            self,
            cursor: 'DBCursor',
            filter_: EvmTransactionsFilterQuery,
    ) -> list[EvmTransaction]:
        """Returns a list of evm transactions optionally filtered by
        the given filter query

        This function can raise:
        - pysqlcipher3.dbapi2.OperationalError if the SQL query fails due to invalid
        filtering arguments.
        """
        query, bindings = filter_.prepare()
        query, bindings = self._form_evm_transaction_dbquery(query, bindings)
        grouped_transactions: dict[int, tuple[Any, ...]] = {}  # Group results by transaction identifier  # noqa: E501
        for result in cursor.execute(query, bindings):
            if (tx_identifier := result[12]) not in grouped_transactions:  # Store base transaction data + empty auth list  # noqa: E501
                grouped_transactions[tx_identifier] = (*result[:self.AUTHORIZATION_DATA_START_INDEX], [])  # noqa: E501

            if (nonce := result[self.AUTHORIZATION_DATA_START_INDEX]) is not None:  # add authorizations if they exist  # noqa: E501
                grouped_transactions[tx_identifier][self.AUTHORIZATION_DATA_START_INDEX].append((nonce, result[self.AUTHORIZATION_DATA_START_INDEX + 1]))  # (nonce, delegated_address)  # noqa: E501

        evm_transactions = []
        for tx_data in grouped_transactions.values():
            try:
                evm_transactions.append(self._build_evm_transaction(tx_data[:-1], tx_data[-1]))
            except DeserializationError as e:
                self.db.msg_aggregator.add_error(
                    f'Error deserializing evm transaction from the DB. '
                    f'Skipping it. Error was: {e!s}',
                )
                continue

        return evm_transactions

    def delete_evm_transaction_data(
            self,
            write_cursor: 'DBCursor',
            chain: SUPPORTED_EVM_CHAINS_TYPE | None = None,
            tx_hash: EVMTxHash | None = None,
    ) -> None:
        """Deletes evm transaction related data from the DB.
        Either all data, data related to a single chain or a single chain/tx_hash only"""
        query_ranges_tuples = []
        delete_query = 'DELETE FROM evm_transactions'
        delete_bindings = ()
        if chain is not None:
            chains = [chain]
            delete_query += ' WHERE chain_id = ?'
            delete_bindings = (chain.to_chain_id().serialize_for_db(),)    # type: ignore[assignment]
        else:
            chains = get_args(SUPPORTED_EVM_CHAINS_TYPE)  # type: ignore[assignment]
        if tx_hash is not None:
            delete_query += f' {"WHERE" if len(delete_bindings) == 0 else "AND"} tx_hash=?'
            delete_bindings += (tx_hash,)  # type: ignore

        else:  # for entire chains, clear ranges
            for entry in chains:
                query_ranges_tuples.extend([
                    (f'{entry.to_range_prefix("txs")}\\_%', '\\'),
                    (f'{entry.to_range_prefix("internaltxs")}\\_%', '\\'),
                    (f'{entry.to_range_prefix("tokentxs")}\\_%', '\\'),
                ])
                write_cursor.executemany(
                    'DELETE FROM used_query_ranges WHERE name LIKE ? ESCAPE ?;',
                    query_ranges_tuples,
                )

        write_cursor.execute(delete_query, delete_bindings)  # finally delete transactions

    def get_transaction_hashes_no_receipt(
            self,
            tx_filter_query: EvmTransactionsFilterQuery | None,
            limit: int | None,
    ) -> list[EVMTxHash]:
        querystr = 'SELECT DISTINCT evm_transactions.tx_hash FROM evm_transactions '
        bindings = ()
        if tx_filter_query is not None:
            filter_query, bindings = tx_filter_query.prepare(with_order=False, with_pagination=False)  # type: ignore  # noqa: E501
            querystr += filter_query + ' AND '
        else:
            querystr += ' WHERE '

        querystr += 'evm_transactions.identifier NOT IN (SELECT tx_id from evmtx_receipts)'
        if limit is not None:
            querystr += 'LIMIT ?'
            bindings = (*bindings, limit)  # type: ignore

        hashes = []
        with self.db.conn.read_ctx() as cursor:
            for entry in cursor.execute(querystr, bindings):
                try:
                    hashes.append(deserialize_evm_tx_hash(entry[0]))
                except DeserializationError as e:
                    log.debug(f'Got error {e!s} while deserializing tx_hash {entry[0]} from the DB')  # noqa: E501

        return hashes

    def deserialize_tx_hash_from_db(self, raw_tx_hash: bytes) -> EVMTxHash:
        """Given a raw tx hash from the DB, deserialize it to an EVMTxHash"""
        return deserialize_evm_tx_hash(raw_tx_hash)

    def _get_txs_not_decoded_column_and_query(self) -> tuple[str, str]:
        return 'C.tx_hash', (
            'evmtx_receipts AS A LEFT OUTER JOIN evm_tx_mappings AS B ON A.tx_id=B.tx_id '
            'LEFT JOIN evm_transactions AS C ON A.tx_id=C.identifier '
        )

    def add_or_ignore_receipt_data(
            self,
            write_cursor: 'DBCursor',
            chain_id: ChainID,
            data: dict[str, Any],
    ) -> int:
        """Add tx receipt data as they are returned by the chain to the DB

        Also need to provide the chain id.

        This assumes the transaction is already in the DB. If the receipt data
        is already in the DB do nothing.

        Returns the db identifier of the transaction corresponding to this receipt.
        May raise:
        - Key Error if any of the expected fields are missing
        - DeserializationError if there is a problem deserializing a value
        - pysqlcipher3.dbapi2.IntegrityError if the transaction hash is not in the DB:
        """
        tx_hash_b = hexstring_to_bytes(data['transactionHash'])
        # some nodes miss the type field for older non EIP1559 transactions. So assume legacy (0)
        tx_type = deserialize_int_from_hex_or_int(data.get('type', '0x0'), location='receipt data insertion')  # noqa: E501
        status = data.get('status', 1)  # status may be missing for older txs. Assume 1.
        serialized_chain_id = chain_id.serialize_for_db()
        if status is None:
            status = 1

        contract_address = deserialize_evm_address(data['contractAddress']) if data['contractAddress'] else None  # noqa: E501
        tx_id = write_cursor.execute(
            'SELECT identifier from evm_transactions WHERE tx_hash=? AND chain_id=?',
            (tx_hash_b, serialized_chain_id),
        ).fetchone()[0]

        try:
            write_cursor.execute(
                'INSERT INTO evmtx_receipts (tx_id, contract_address, status, type) '
                'VALUES(?, ?, ?, ?) ',
                (tx_id, contract_address, status, tx_type),
            )
        except sqlcipher.IntegrityError as e:  # pylint: disable=no-member
            if 'UNIQUE constraint failed: evmtx_receipts.tx_id' not in str(e):
                log.error(f'Failed to insert transaction {tx_id} receipt to the DB due to {e!s}')
                raise
            return tx_id  # otherwise something else added the receipt so we continue

        for log_entry in data['logs']:
            write_cursor.execute(
                'INSERT INTO evmtx_receipt_logs (tx_id, log_index, data, address) '
                'VALUES(? ,? ,? ,?)',
                (
                    tx_id,
                    log_entry['logIndex'],
                    hexstring_to_bytes(log_entry['data']),
                    deserialize_evm_address(log_entry['address']),
                ),
            )
            log_id = write_cursor.lastrowid
            topic_tuples = []
            for idx, topic in enumerate(log_entry['topics']):
                topic_tuples.append((
                    log_id,
                    hexstring_to_bytes(topic),
                    idx,
                ))
            if len(topic_tuples) != 0:
                write_cursor.executemany(
                    'INSERT INTO evmtx_receipt_log_topics (log, topic, topic_index) '
                    'VALUES(? ,? ,?)',
                    topic_tuples,
                )

        return tx_id

    def get_receipt(
            self,
            cursor: 'DBCursor',
            tx_hash: EVMTxHash,
            chain_id: ChainID,
    ) -> EvmTxReceipt | None:
        """Get the evm receipt for the given tx_hash and chain id"""
        chain_id_serialized = chain_id.serialize_for_db()
        result = cursor.execute(
            'SELECT identifier from evm_transactions WHERE tx_hash=? AND chain_id=?',
            (tx_hash, chain_id_serialized),
        ).fetchone()
        if result is None:
            return None
        tx_id = result[0]
        result = cursor.execute(
            'SELECT contract_address, status, type from evmtx_receipts WHERE tx_id=?',
            (tx_id,),
        ).fetchone()
        if result is None:
            return None

        tx_receipt = EvmTxReceipt(
            tx_hash=tx_hash,
            chain_id=chain_id,
            contract_address=result[0],
            status=bool(result[1]),  # works since value is either 0 or 1
            tx_type=result[2],
        )

        cursor.execute(
            'SELECT identifier, log_index, data, address from evmtx_receipt_logs WHERE tx_id=?',
            (tx_id,))
        with self.db.conn.read_ctx() as other_cursor:
            for result in cursor:
                tx_receipt_log = EvmTxReceiptLog(
                    log_index=result[1],
                    data=result[2],
                    address=result[3],
                )
                other_cursor.execute(
                    'SELECT topic from evmtx_receipt_log_topics '
                    'WHERE log=? ORDER BY topic_index ASC',
                    (result[0],),
                )
                tx_receipt_log.topics = [x[0] for x in other_cursor]
                if (
                    len(tx_receipt_log.topics) == 0 and
                    tx_receipt_log.address not in (
                        CONSOLIDATION_REQUEST_CONTRACT,
                        WITHDRAWAL_REQUEST_CONTRACT,
                    )
                ):  # skip anonymous logs unless they are from specific addresses whose decoders properly handle it.  # noqa: E501
                    log.debug(f'Ignoring anonymous tx log in {tx_hash.hex()} at {chain_id}')
                    continue

                tx_receipt.logs.append(tx_receipt_log)

        return tx_receipt

    def delete_transactions(
            self,
            write_cursor: 'DBCursor',
            address: ChecksumEvmAddress,
            chain: SUPPORTED_EVM_CHAINS_TYPE,
    ) -> None:
        """Delete all of the particular evm chain transactions related data
        to the given address from the DB.

        So transactions, receipts, logs and decoded events, except for those
        whose events are customized.
        """
        dbevents = DBHistoryEvents(self.db)
        chain_id = chain.to_chain_id()
        chain_id_serialized = chain_id.serialize_for_db()
        write_cursor.executemany(
            'DELETE FROM used_query_ranges WHERE name=?;',
            [
                (f'{chain.to_range_prefix("txs")}_{address}',),
                (f'{chain.to_range_prefix("internaltxs")}_{address}',),
                (f'{chain.to_range_prefix("tokentxs")}_{address}',),
            ],
        )
        # Get all tx_hashes that are touched by this address and no other address for the chain
        result = write_cursor.execute(
            'SELECT A.tx_hash, A.identifier from evmtx_address_mappings AS B INNER JOIN '
            'evm_transactions AS A ON A.identifier=B.tx_id WHERE B.address=? AND A.chain_id=? '
            'AND B.tx_id NOT IN (SELECT tx_id from evmtx_address_mappings WHERE address!=? '
            'AND chain_id=?)',
            (address, chain_id_serialized, address, chain_id_serialized),
        )
        tx_hashes = []
        tx_ids = []
        for tx_hash, tx_id in result:
            tx_hashes.append(deserialize_evm_tx_hash(tx_hash))
            tx_ids.append(tx_id)

        genesis_tx_id = None
        if len(tx_hashes) == 0:
            # Need to handle the genesis tx separately since our single genesis tx contains
            # multiple genesis transactions from multiple addresses.
            genesis_tx_id = write_cursor.execute(
                'SELECT tx_id FROM evmtx_address_mappings AS M LEFT JOIN evm_transactions AS T '
                'ON T.identifier=M.tx_id WHERE T.tx_hash=? AND T.chain_id=?',
                (GENESIS_HASH, chain_id_serialized),
            ).fetchone()
            if genesis_tx_id is None:
                return
            genesis_tx_id = genesis_tx_id[0]

        dbevents.delete_events_by_tx_ref(
            write_cursor=write_cursor,
            tx_refs=tx_hashes,
            location=Location.from_chain_id(chain_id),
        )
        write_cursor.execute(  # delete genesis tx events related to the provided address
            'DELETE FROM history_events WHERE identifier IN ('
            'SELECT H.identifier from history_events H INNER JOIN chain_events_info C '
            'ON H.identifier=C.identifier WHERE C.tx_ref=? AND H.location_label=?)',
            (GENESIS_HASH, address),
        )
        genesis_events_count = write_cursor.execute(
            'SELECT COUNT (*) FROM history_events H INNER JOIN chain_events_info C'
            ' WHERE H.identifier=C.identifier and C.tx_ref=?',
            (GENESIS_HASH,),
        ).fetchone()[0]
        if genesis_events_count == 0:
            # If there are no more events in the genesis tx, delete it
            tx_hashes.append(GENESIS_HASH)
            if genesis_tx_id is not None:
                tx_ids.append(genesis_tx_id)

        # Now delete all relevant transactions. By deleting all relevant transactions all tables
        # are cleared thanks to cascading (except for history_events which was cleared above)
        write_cursor.executemany(
            'DELETE FROM evm_transactions WHERE tx_hash=? AND chain_id=? AND tx_hash NOT IN (SELECT tx_ref FROM chain_events_info)',  # noqa: E501
            [(x, chain_id_serialized) for x in tx_hashes],
        )
        # Delete all remaining evm_tx_mappings so decoding can happen again
        write_cursor.executemany(
            'DELETE FROM evm_tx_mappings WHERE tx_id=? AND value IN (?, ?)',
            [(x, TX_DECODED, TX_SPAM) for x in tx_ids],
        )
        # Delete any key_value_cache entries
        write_cursor.executemany(
            'DELETE FROM key_value_cache WHERE name LIKE ?',
            [(f'{EXTRAINTERNALTXPREFIX}_{chain_id.value}_%_{tx_hash.hex()}',) for tx_hash in tx_hashes],  # noqa: E501
        )

    def get_queried_range(
            self,
            cursor: 'DBCursor',
            address: ChecksumEvmAddress,
            chain: SUPPORTED_EVM_CHAINS_TYPE,
    ) -> tuple[Timestamp, Timestamp]:
        """Gets the most conservative range that was queried for the
        transactions of an address for a specific evm chain

        That means the least common denominator of normal, internal and token transactions
        """
        starts = []
        ends = []
        prefixes = [chain.to_range_prefix('txs'), chain.to_range_prefix('internaltxs'), chain.to_range_prefix('tokentxs')]  # noqa: E501
        for prefix in prefixes:
            tx_range = self.db.get_used_query_range(cursor, f'{prefix}_{address}')
            if tx_range is None:  # if any range is missing then we gotta requery
                return Timestamp(0), Timestamp(0)

            starts.append(tx_range[0])
            ends.append(tx_range[1])

        return max(starts), min(ends)

    def get_max_genesis_trace_id(self, chain_id: ChainID) -> int:
        """Get the max trace id of genesis internal transactions from the database.
        If no internal transactions were found, returns 0 (zero)."""
        with self.db.conn.read_ctx() as cursor:
            trace_id, = cursor.execute(
                'SELECT MAX(trace_id) from evm_internal_transactions AS ITX '
                'INNER JOIN evm_transactions AS TX ON ITX.parent_tx=TX.identifier '
                'WHERE TX.tx_hash=? and chain_id=?',
                (GENESIS_HASH, chain_id.serialize_for_db()),
            ).fetchone()
        return trace_id if trace_id is not None else 0

    def get_or_create_genesis_transaction(
            self,
            account: ChecksumEvmAddress,
            chain_id: SUPPORTED_CHAIN_IDS,
    ) -> EvmTransaction:
        with self.db.conn.read_ctx() as cursor:
            tx_in_db = self.get_transactions(
                cursor=cursor,
                filter_=EvmTransactionsFilterQuery.make(
                    tx_hash=GENESIS_HASH,
                    accounts=[EvmAccount(address=account)],
                    chain_id=chain_id,
                ),
            )
        if len(tx_in_db) == 1:
            tx = tx_in_db[0]
        else:
            if chain_id == ChainID.ETHEREUM:
                timestamp = ETHEREUM_GENESIS
            elif chain_id == ChainID.OPTIMISM:
                timestamp = OPTIMISM_GENESIS
            elif chain_id == ChainID.ARBITRUM_ONE:
                timestamp = ARBITRUM_ONE_GENESIS
            elif chain_id == ChainID.BASE:
                timestamp = BASE_GENESIS
            elif chain_id == ChainID.GNOSIS:
                timestamp = GNOSIS_GENESIS
            elif chain_id == ChainID.SCROLL:
                timestamp = SCROLL_GENESIS
            elif chain_id == ChainID.BINANCE_SC:
                timestamp = BINANCE_SC_GENESIS
            else:
                timestamp = POLYGON_POS_GENESIS
            tx = EvmTransaction(
                chain_id=chain_id,
                timestamp=timestamp,
                block_number=0,
                tx_hash=GENESIS_HASH,
                from_address=ZERO_ADDRESS,
                to_address=None,
                value=0,
                gas=0,
                gas_price=0,
                gas_used=0,
                input_data=b'',
                nonce=0,
            )
            with self.db.user_write() as cursor:
                self.add_transactions(
                    write_cursor=cursor,
                    evm_transactions=[tx],
                    relevant_address=account,
                )
        return tx

    def _form_evm_transaction_dbquery(self, query: str, bindings: list[Any]) -> tuple[str, list]:
        """Constructs SQL query and bindings for EVM transactions with authorization data"""
        base_select = (
            'SELECT evm_transactions.tx_hash, evm_transactions.chain_id, '
            'timestamp, block_number, from_address, to_address, value, evm_transactions.gas, '
            'gas_price, evm_transactions.gas_used, input_data, evm_transactions.nonce, '
            'identifier, auth.nonce AS auth_nonce, auth.delegated_address '
            'FROM evm_transactions LEFT JOIN evm_transactions_authorizations AS auth '
            'ON evm_transactions.identifier = auth.tx_id '
        )
        return f'{base_select} {query}', bindings

    def _build_evm_transaction(self, result: tuple[Any, ...], authorization_list_result: list[tuple[int, ChecksumEvmAddress]]) -> EvmTransaction:  # noqa: E501
        """Construct an EvmTransaction from db query result.

        `result` is a tuple containing core transaction fields from the `evm_transactions` table.
        The `authorization_list_result` is a list of (nonce, delegated_address) tuples from the
        `evm_transaction_authorizations` table.

        May raise:
        - DeserializationError
        """
        return EvmTransaction(
            tx_hash=deserialize_evm_tx_hash(result[0]),
            chain_id=ChainID.deserialize_from_db(result[1]),
            timestamp=deserialize_timestamp(result[2]),
            block_number=result[3],
            from_address=result[4],
            to_address=result[5],
            value=int(result[6]),
            gas=int(result[7]),
            gas_price=int(result[8]),
            gas_used=int(result[9]),
            input_data=result[10],
            nonce=result[11],
            db_id=result[12],
            authorization_list=None if len(authorization_list_result) == 0 else [
                EvmTransactionAuthorization(nonce=entry[0], delegated_address=entry[1])
                for entry in authorization_list_result
            ],
        )

    def count_evm_transactions(self, chain_id: SUPPORTED_CHAIN_IDS) -> int:
        """Counts the number of unique evm transactions in the requested chain"""
        query, bindings = EvmTransactionsFilterQuery.make(
            chain_id=chain_id,
        ).prepare(with_pagination=False)
        query = 'SELECT COUNT(DISTINCT evm_transactions.tx_hash) FROM evm_transactions ' + query
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(query, bindings)
            return cursor.fetchone()[0]

    def get_transaction_block_by_hash(self, cursor: 'DBCursor', tx_hash: EVMTxHash) -> int | None:
        """Return the block number of a transaction"""
        cursor.execute('SELECT block_number FROM evm_transactions WHERE tx_hash=?', (tx_hash,))
        if (result := cursor.fetchone()) is None:
            return None
        return result[0]

    def count_transactions_in_range(
            self,
            chain_id: SUPPORTED_CHAIN_IDS,
            from_ts: Timestamp,
            to_ts: Timestamp,
    ) -> int:
        """Return the number of transactions between from_ts and to_ts for a given chain"""
        with self.db.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT COUNT(*) FROM evm_transactions WHERE chain_id = ? AND timestamp BETWEEN ? AND ?',  # noqa: E501
                (chain_id.serialize_for_db(), from_ts, to_ts),
            )
            return cursor.fetchone()[0]
