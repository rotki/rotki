import logging
from typing import TYPE_CHECKING

from rotkehlchen.chain.bitcoin.types import BitcoinTx, BtcTxIO, BtcTxIODirection
from rotkehlchen.db.constants import TX_DECODED
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import BTCAddress, BTCTxId, Timestamp
from rotkehlchen.utils.misc import btc_to_satoshis, satoshis_to_btc

if TYPE_CHECKING:
    from collections.abc import Sequence

    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.types import BLOCKCHAIN_LOCATIONS_TYPE

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DBBitcoinTx:
    """Database handler for bitcoin and bitcoin cash transactions.

    Both chains share the tables and are told apart by the location column, mirroring the
    single manager that serves them.
    """

    def __init__(self, database: DBHandler) -> None:
        self.db = database

    def add_transactions(
            self,
            write_cursor: DBCursor,
            transactions: Sequence[BitcoinTx],
            location: BLOCKCHAIN_LOCATIONS_TYPE,
            relevant_addresses: Sequence[BTCAddress],
    ) -> set[BTCTxId]:
        """Save the given transactions along with the addresses they were queried for.

        A transaction that is already saved has its TxIOs merged with the incoming ones
        instead of being replaced, since the APIs may return only the TxIOs touching the
        queried addresses. TxIOs are identified by their real index in the transaction, so
        merging two such partial views completes the saved copy rather than duplicating it.

        Returns the ids of the transactions that need decoding: the newly saved ones and
        the ones whose saved copy changed, either by gaining TxIOs or by being associated
        with an address that wasn't tracked when they were last decoded.
        """
        to_decode: set[BTCTxId] = set()
        for tx in transactions:
            write_cursor.execute(
                'INSERT OR IGNORE INTO bitcoin_transactions('
                'location, tx_id, timestamp, block_height, fee, vin_count, vout_count'
                ') VALUES(?, ?, ?, ?, ?, ?, ?)',
                (
                    location.serialize_for_db(),
                    tx.tx_id,
                    tx.timestamp,
                    tx.block_height,
                    btc_to_satoshis(tx.fee),
                    tx.vin_count,
                    tx.vout_count,
                ),
            )
            if (is_new := write_cursor.rowcount == 1):
                db_id = write_cursor.lastrowid
            else:
                db_id = write_cursor.execute(
                    'SELECT identifier FROM bitcoin_transactions WHERE location=? AND tx_id=?',
                    (location.serialize_for_db(), tx.tx_id),
                ).fetchone()[0]
                # A saved copy that was missing TxIOs may now know their real number.
                write_cursor.execute(
                    'UPDATE bitcoin_transactions SET vin_count=COALESCE(?, vin_count), '
                    'vout_count=COALESCE(?, vout_count) WHERE identifier=?',
                    (tx.vin_count, tx.vout_count, db_id),
                )

            changed = is_new
            for tx_io in tx.inputs + tx.outputs:
                write_cursor.execute(
                    'INSERT OR IGNORE INTO bitcoin_tx_io('
                    'tx_id, direction, io_index, value, address, script'
                    ') VALUES(?, ?, ?, ?, ?, ?)',
                    (
                        db_id,
                        tx_io.direction.serialize_for_db(),
                        tx_io.io_index,
                        btc_to_satoshis(tx_io.value),
                        tx_io.address,
                        tx_io.script,
                    ),
                )
                changed |= write_cursor.rowcount == 1 and not is_new

            for address in relevant_addresses:
                write_cursor.execute(
                    'INSERT OR IGNORE INTO bitcointx_address_mappings(tx_id, address) '
                    'VALUES(?, ?)',
                    (db_id, address),
                )
                changed |= write_cursor.rowcount == 1 and not is_new

            if changed:
                to_decode.add(BTCTxId(tx.tx_id))
                if not is_new:  # its decoded events no longer match the saved transaction
                    write_cursor.execute(
                        'DELETE FROM bitcoin_tx_mappings WHERE tx_id=? AND value=?',
                        (db_id, TX_DECODED),
                    )

        return to_decode

    def get_transactions(
            self,
            cursor: DBCursor,
            location: BLOCKCHAIN_LOCATIONS_TYPE,
            tx_ids: Sequence[BTCTxId] | None = None,
            undecoded_only: bool = False,
    ) -> list[BitcoinTx]:
        """Get the saved transactions of the given location, ordered oldest to newest.

        If tx_ids is given only those transactions are returned, and if undecoded_only is
        set the ones already decoded are skipped.
        """
        transactions: list[BitcoinTx] = []
        for query, bindings in self._transaction_queries(
            location=location,
            tx_ids=tx_ids,
            undecoded_only=undecoded_only,
        ):
            txs_data = cursor.execute(
                f'SELECT identifier, tx_id, timestamp, block_height, fee, vin_count, vout_count '
                f'FROM bitcoin_transactions {query} ORDER BY timestamp ASC, identifier ASC',
                bindings,
            ).fetchall()  # materialized since the TxIO query below needs the cursor
            if len(txs_data) == 0:
                continue

            tx_ios: dict[int, dict[BtcTxIODirection, list[BtcTxIO]]] = {}
            for chunk, placeholders in get_query_chunks(data=[x[0] for x in txs_data]):
                for db_id, raw_direction, io_index, value, address, script in cursor.execute(
                    f'SELECT tx_id, direction, io_index, value, address, script '
                    f'FROM bitcoin_tx_io WHERE tx_id IN ({placeholders}) ORDER BY io_index ASC',
                    chunk,
                ):
                    direction = BtcTxIODirection.deserialize_from_db(raw_direction)
                    tx_ios.setdefault(db_id, {}).setdefault(direction, []).append(BtcTxIO(
                        value=satoshis_to_btc(value),
                        script=script,
                        address=address,
                        direction=direction,
                        io_index=io_index,
                    ))

            transactions.extend(BitcoinTx(
                tx_id=tx_id,
                timestamp=Timestamp(timestamp),
                block_height=block_height,
                fee=satoshis_to_btc(fee),
                inputs=tx_ios.get(db_id, {}).get(BtcTxIODirection.INPUT, []),
                outputs=tx_ios.get(db_id, {}).get(BtcTxIODirection.OUTPUT, []),
                vin_count=vin_count,
                vout_count=vout_count,
            ) for db_id, tx_id, timestamp, block_height, fee, vin_count, vout_count in txs_data)

        return transactions

    def get_transaction_ids(
            self,
            cursor: DBCursor,
            location: BLOCKCHAIN_LOCATIONS_TYPE,
            tx_ids: Sequence[BTCTxId] | None = None,
            undecoded_only: bool = False,
    ) -> list[BTCTxId]:
        """Get the ids of the saved transactions of the given location, oldest to newest.
        Filtered the same way as get_transactions, but without reading the transactions
        themselves, so that a caller working through them in chunks doesn't need to hold
        every transaction and all its TxIOs in memory to know what to work on.
        """
        result: list[BTCTxId] = []
        for query, bindings in self._transaction_queries(
            location=location,
            tx_ids=tx_ids,
            undecoded_only=undecoded_only,
        ):
            result.extend(BTCTxId(x[0]) for x in cursor.execute(
                f'SELECT tx_id FROM bitcoin_transactions {query} '
                f'ORDER BY timestamp ASC, identifier ASC',
                bindings,
            ))

        return result

    def get_transaction_ids_for_address(
            self,
            cursor: DBCursor,
            location: BLOCKCHAIN_LOCATIONS_TYPE,
            address: BTCAddress,
    ) -> list[BTCTxId]:
        """Get the ids of the saved transactions that have a TxIO belonging to the address.

        Used to redecode the transactions an address takes part in when it starts being
        tracked, since the events of a bitcoin transaction depend on which of its addresses
        are tracked. Only the transactions already saved are found this way, so the address'
        own history still has to be queried.
        """
        return [BTCTxId(x[0]) for x in cursor.execute(
            'SELECT DISTINCT T.tx_id FROM bitcoin_transactions AS T INNER JOIN bitcoin_tx_io '
            'AS IO ON IO.tx_id=T.identifier WHERE T.location=? AND IO.address=?',
            (location.serialize_for_db(), address),
        )]

    def count_undecoded_transactions(
            self,
            cursor: DBCursor,
            location: BLOCKCHAIN_LOCATIONS_TYPE,
    ) -> int:
        query, bindings = next(iter(self._transaction_queries(
            location=location,
            undecoded_only=True,
        )))
        return cursor.execute(
            f'SELECT COUNT(*) FROM bitcoin_transactions {query}', bindings,
        ).fetchone()[0]

    def set_decoded(
            self,
            write_cursor: DBCursor,
            location: BLOCKCHAIN_LOCATIONS_TYPE,
            tx_ids: Sequence[BTCTxId],
    ) -> None:
        """Mark the given transactions as decoded."""
        for chunk, placeholders in get_query_chunks(data=tx_ids):
            write_cursor.execute(
                f'INSERT OR IGNORE INTO bitcoin_tx_mappings(tx_id, value) '
                f'SELECT identifier, ? FROM bitcoin_transactions '
                f'WHERE location=? AND tx_id IN ({placeholders})',
                [TX_DECODED, location.serialize_for_db(), *chunk],
            )

    def reset_decoded_state(
            self,
            write_cursor: DBCursor,
            location: BLOCKCHAIN_LOCATIONS_TYPE,
            tx_ids: Sequence[BTCTxId] | None = None,
    ) -> None:
        """Mark the given transactions as needing to be decoded again.
        If no transactions are given, all the transactions of the location are marked.
        """
        for query, bindings in self._transaction_queries(location=location, tx_ids=tx_ids):
            write_cursor.execute(
                f'DELETE FROM bitcoin_tx_mappings WHERE value=? AND tx_id IN '
                f'(SELECT identifier FROM bitcoin_transactions {query})',
                [TX_DECODED, *bindings],
            )

    def delete_transactions(
            self,
            write_cursor: DBCursor,
            location: BLOCKCHAIN_LOCATIONS_TYPE,
            tx_ids: Sequence[BTCTxId] | None = None,
    ) -> None:
        """Delete the saved transactions of the given location, all of them if no ids are
        given. Their TxIOs, address mappings and decoding state go with them via cascade.
        """
        for query, bindings in self._transaction_queries(location=location, tx_ids=tx_ids):
            write_cursor.execute(f'DELETE FROM bitcoin_transactions {query}', bindings)

    def delete_data_for_address(
            self,
            write_cursor: DBCursor,
            location: BLOCKCHAIN_LOCATIONS_TYPE,
            address: BTCAddress,
    ) -> None:
        """Delete the transactions that were queried only for the given address, along with
        their events. Transactions another tracked address was also queried for are kept, but
        marked as needing decoding again: the events of a bitcoin transaction depend on which
        of its addresses are tracked, so what was decoded while this one still was is now
        outdated (a transfer between two owned addresses becomes a plain spend, for one).
        """
        own_tx_ids: list[BTCTxId] = []
        shared_tx_ids: list[BTCTxId] = []
        for tx_id, is_shared in write_cursor.execute(
            'SELECT T.tx_id, EXISTS(SELECT 1 FROM bitcointx_address_mappings WHERE tx_id=M.tx_id '
            'AND address!=?) FROM bitcointx_address_mappings AS M INNER JOIN bitcoin_transactions '
            'AS T ON T.identifier=M.tx_id WHERE M.address=? AND T.location=?',
            (address, address, location.serialize_for_db()),
        ).fetchall():  # materialized since the writes below reuse the cursor
            (shared_tx_ids if is_shared == 1 else own_tx_ids).append(BTCTxId(tx_id))

        if len(own_tx_ids) != 0:
            DBHistoryEvents(self.db).delete_events_by_tx_ref(
                write_cursor=write_cursor,
                tx_refs=own_tx_ids,
                location=location,
                customized_handling='delete',
            )
            self.delete_transactions(
                write_cursor=write_cursor,
                location=location,
                tx_ids=own_tx_ids,
            )

        if len(shared_tx_ids) != 0:
            self.reset_decoded_state(
                write_cursor=write_cursor,
                location=location,
                tx_ids=shared_tx_ids,
            )

        # Drop what the address left on the transactions it shared with another one, so that
        # it no longer counts as a reason to keep them once that other address goes too.
        write_cursor.execute(
            'DELETE FROM bitcointx_address_mappings WHERE address=? AND tx_id IN '
            '(SELECT identifier FROM bitcoin_transactions WHERE location=?)',
            (address, location.serialize_for_db()),
        )

    @staticmethod
    def _transaction_queries(
            location: BLOCKCHAIN_LOCATIONS_TYPE,
            tx_ids: Sequence[BTCTxId] | None = None,
            undecoded_only: bool = False,
    ) -> list[tuple[str, list[str | int]]]:
        """Build the where clauses selecting transactions of a location, chunked over the
        given tx ids so that an arbitrary number of them can be queried. Yields a single
        location-wide clause when no ids are given.
        """
        where_str = 'WHERE location=?'
        if undecoded_only:
            where_str += f' AND identifier NOT IN (SELECT tx_id FROM bitcoin_tx_mappings WHERE value={TX_DECODED})'  # noqa: E501

        if tx_ids is None:
            return [(where_str, [location.serialize_for_db()])]

        return [
            (f'{where_str} AND tx_id IN ({placeholders})', [location.serialize_for_db(), *chunk])
            for chunk, placeholders in get_query_chunks(data=tx_ids)
        ]
