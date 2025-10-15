import logging
from typing import TYPE_CHECKING, Final

from solders.solders import Signature

from rotkehlchen.api.websockets.typedefs import (
    TransactionStatusStep,
    TransactionStatusSubType,
    WSMessageType,
)
from rotkehlchen.chain.solana.types import SolanaTransaction
from rotkehlchen.db.filtering import SolanaTransactionsFilterQuery
from rotkehlchen.db.solanatx import DBSolanaTx
from rotkehlchen.errors.misc import MissingAPIKey, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.helius import Helius
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import SolanaAddress, SupportedBlockchain, Timestamp
from rotkehlchen.utils.misc import get_chunks, ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

# The number of txs to query from RPCs before saving progress in the DB.
# Using the api.mainnet-beta.solana.com RPC 10 txs took ~1 minute.
RPC_TX_BATCH_SIZE: Final = 10


class SolanaTransactions:

    def __init__(
            self,
            node_inquirer: 'SolanaInquirer',
            database: 'DBHandler',
            helius: Helius,
    ) -> None:
        self.node_inquirer = node_inquirer
        self.database = database
        self.dbtx = DBSolanaTx(database=database)
        self.helius = helius

    def get_or_create_transaction(
            self,
            signature: Signature,
            relevant_address: SolanaAddress | None = None,
    ) -> SolanaTransaction:
        """Gets a transaction from the DB or from onchain. If it must be queried from onchain, it
        is also saved to the DB.
        May raise:
        - RemoteError if there is a problem with querying the external service.
        - DeserializationError if there is a problem deserializing the transaction data.
        """
        with self.database.conn.read_ctx() as cursor:
            if len(txs := self.dbtx.get_transactions(
                cursor=cursor,
                filter_=SolanaTransactionsFilterQuery.make(signature=signature),
            )) == 1:
                return txs[0]

        tx, token_accounts_mapping = self.node_inquirer.get_transaction_for_signature(
            signature=signature,
        )
        with self.database.conn.write_ctx() as write_cursor:
            self.dbtx.add_transactions(
                write_cursor=write_cursor,
                solana_transactions=[tx],
                relevant_address=relevant_address,
            )
            self.dbtx.add_token_account_mappings(
                write_cursor=write_cursor,
                token_accounts_mappings=token_accounts_mapping,
            )

        return tx

    def _send_tx_status_message(
            self,
            address: SolanaAddress,
            period: tuple[Timestamp, Timestamp],
            status: TransactionStatusStep,
    ) -> None:
        self.database.msg_aggregator.add_message(
            message_type=WSMessageType.TRANSACTION_STATUS,
            data={
                'address': address,
                'chain': SupportedBlockchain.SOLANA.value,
                'subtype': str(TransactionStatusSubType.SOLANA),
                'period': period,
                'status': str(status),
            },
        )

    def query_transactions_for_address(self, address: SolanaAddress) -> None:
        """Query the transactions for the given address and save them to the DB.
        Only queries new transactions if there are already transactions in the DB.
        May raise RemoteError if there is a problem with querying the external service.
        """
        last_existing_sig, start_ts, end_ts = None, Timestamp(0), ts_now()
        with self.database.conn.read_ctx() as cursor:
            cursor.execute(
                'SELECT st.signature, max(st.block_time) FROM solana_transactions st '
                'JOIN solanatx_address_mappings sam ON st.identifier == sam.tx_id '
                'WHERE sam.address = ?',
                (address,),
            )
            if (max_result := cursor.fetchone()) is not None and None not in max_result:
                last_existing_sig = Signature.from_bytes(max_result[0])
                start_ts = Timestamp(max_result[1])

        self._send_tx_status_message(
            address=address,
            period=(start_ts, end_ts),
            status=TransactionStatusStep.QUERYING_TRANSACTIONS_STARTED,
        )

        # Get the list of signatures from the RPCs and query the corresponding txs
        signatures = self.node_inquirer.query_tx_signatures_for_address(
            address=address,
            until=last_existing_sig,
        )
        self.query_transactions_for_signatures(
            signatures=signatures,
            relevant_address=address,
        )

        self._send_tx_status_message(
            address=address,
            period=(start_ts, end_ts),
            status=TransactionStatusStep.QUERYING_TRANSACTIONS_FINISHED,
        )

    def query_transactions_for_signatures(
            self,
            signatures: list[Signature],
            relevant_address: SolanaAddress,
    ) -> None:
        """Query the transactions for the given signatures from either Helius or the RPCs,
        and save them to the DB.
        """
        try:
            self.helius.get_transactions(
                signatures=[str(x) for x in signatures],
                relevant_address=relevant_address,
            )
        except (RemoteError, MissingAPIKey) as e:
            log.debug(
                f'Unable to query solana transactions from Helius due to {e!s} '
                f'Falling back to querying from the RPCs for address {relevant_address}.',
            )
        else:
            return

        solana_tx_db = DBSolanaTx(database=self.database)
        for chunk in get_chunks(signatures, RPC_TX_BATCH_SIZE):
            txs, token_accounts_mappings = [], {}
            for signature in chunk:
                try:
                    tx, token_accounts_mapping = self.node_inquirer.get_transaction_for_signature(signature)  # noqa: E501
                    txs.append(tx)
                    token_accounts_mappings.update(token_accounts_mapping)
                except (RemoteError, DeserializationError) as e_:
                    log.error(
                        f'Failed to query solana transaction with signature {signature} '
                        f'from the RPCs due to {e_!s}. Skipping.',
                    )
                    continue

            with self.database.conn.write_ctx() as write_cursor:
                solana_tx_db.add_transactions(
                    write_cursor=write_cursor,
                    solana_transactions=txs,
                    relevant_address=relevant_address,
                )
                solana_tx_db.add_token_account_mappings(
                    write_cursor=write_cursor,
                    token_accounts_mappings=token_accounts_mappings,
                )

    def query_transactions_in_range(
            self,
            address: SolanaAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
    ) -> None:
        """Query any missing transactions for the given address in the given range and
        save them to the DB.

        Since solana txs can't be queried by timestamp, this uses the existing txs on either side
        of the range as the before/until parameters for the query. If these boundary txs are not
        present in the DB for one or both sides of the range, then we query all txs on that side
        to ensure we get all missed transactions for the given range.

        May raise RemoteError if there is a problem querying an external service.
        """
        self._send_tx_status_message(
            address=address,
            period=(start_ts, end_ts),
            status=TransactionStatusStep.QUERYING_TRANSACTIONS_STARTED,
        )
        until_sig, before_sig = None, None
        with self.database.conn.read_ctx() as cursor:
            if len(existing_txs := cursor.execute(
                'SELECT signature, block_time FROM solana_transactions st '
                'JOIN solanatx_address_mappings sam ON st.identifier == sam.tx_id '
                'WHERE sam.address = ? '
                'AND block_time >= COALESCE((SELECT MAX(block_time) FROM solana_transactions WHERE block_time < ?), ?) '  # noqa: E501
                'AND block_time <= COALESCE((SELECT MIN(block_time) FROM solana_transactions WHERE block_time > ?), ?) '  # noqa: E501
                'ORDER BY block_time;',
                (address, start_ts, start_ts, end_ts, end_ts),
            ).fetchall()) != 0:
                first_sig, first_block_time = existing_txs[0]
                if first_block_time <= start_ts:
                    until_sig = Signature(first_sig)

                last_sig, last_block_time = existing_txs[-1]
                if last_block_time >= end_ts:
                    before_sig = Signature(last_sig)

        existing_signatures = [Signature(x) for x, _ in existing_txs]
        if len(sigs_to_query := [x for x in self.node_inquirer.query_tx_signatures_for_address(
            address=address,
            until=until_sig,
            before=before_sig,
        ) if x not in existing_signatures]) == 0:
            return  # There are no missed transactions in the specified range

        self.query_transactions_for_signatures(
            signatures=sigs_to_query,
            relevant_address=address,
        )
        self._send_tx_status_message(
            address=address,
            period=(start_ts, end_ts),
            status=TransactionStatusStep.QUERYING_TRANSACTIONS_FINISHED,
        )
