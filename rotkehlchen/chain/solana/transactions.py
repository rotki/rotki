import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Final, Literal, overload

from solders.solders import Signature

from rotkehlchen.api.websockets.typedefs import (
    TransactionStatusStep,
    TransactionStatusSubType,
    WSMessageType,
)
from rotkehlchen.chain.solana.types import SolanaTransaction, pubkey_to_solana_address
from rotkehlchen.db.filtering import SolanaTransactionsFilterQuery
from rotkehlchen.db.solanatx import DBSolanaTx
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.errors.misc import MissingAPIKey, RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.externalapis.helius import Helius
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_tx_signature
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
        ata_accounts = self.node_inquirer.query_token_accounts_by_owner(account=address)
        with self.database.conn.write_ctx() as write_cursor:
            write_cursor.executemany(
                'INSERT OR IGNORE INTO solana_ata_address_mappings(account, ata_address) VALUES (?, ?)',  # noqa: E501
                [
                    (address, pubkey_to_solana_address(ata_account.pubkey))
                    for ata_account in ata_accounts
                ],
            )

        last_existing_sigs: dict[SolanaAddress, Signature | None] = {}
        start_timestamps, end_ts = set(), ts_now()
        with self.database.conn.read_ctx() as cursor:
            # Query the user address and all its ATAs with the signature and block time of the
            # latest existing tx associated with each address.
            for result in cursor.execute(
                'SELECT address, signature, block_time FROM ('
                '  SELECT addresses.address, st.signature, st.block_time, ROW_NUMBER() OVER ('
                '    PARTITION BY addresses.address ORDER BY st.block_time DESC '
                '  ) as row_num FROM ('
                '    SELECT ? as address UNION '
                '    SELECT ata_address as address FROM solana_ata_address_mappings WHERE account = ? '  # noqa: E501
                '  ) AS addresses '
                '  LEFT JOIN solanatx_address_mappings sam ON sam.address = addresses.address '
                '  LEFT JOIN solana_transactions st ON st.identifier = sam.tx_id '
                ') WHERE row_num = 1',
                (address, address),
            ):
                if result is None or result[0] is None:
                    continue

                last_existing_sigs[SolanaAddress(result[0])] = (
                    None if result[1] is None else deserialize_tx_signature(result[1])
                )
                start_timestamps.add(Timestamp(0 if result[2] is None else result[2]))

        self._send_tx_status_message(
            address=address,
            period=((min_start_ts := min(start_timestamps, default=Timestamp(0))), end_ts),
            status=TransactionStatusStep.QUERYING_TRANSACTIONS_STARTED,
        )
        log.debug(
            f'Starting solana transaction query for {address}. '
            f'Will query signatures for {len(last_existing_sigs)} addresses/ATAs.',
        )
        for ata_or_account, last_existing_sig in last_existing_sigs.items():
            # Get the list of signatures from the RPCs and query the corresponding txs
            log.debug(
                f'Querying solana signatures for {ata_or_account} belonging to {address} '
                f'with until={last_existing_sig}',
            )
            signatures = self.node_inquirer.query_tx_signatures_for_address(
                address=ata_or_account,
                until=last_existing_sig,
            )
            log.debug(
                f'Finished querying solana signatures for {ata_or_account} belonging to '
                f'{address}. Got {len(signatures)} signatures.',
            )
            self.query_transactions_for_signatures(
                signatures=signatures,
                relevant_address=ata_or_account,
            )
            log.debug(
                f'Finished querying solana transactions for {ata_or_account} belonging to '
                f'{address}.',
            )

        self._send_tx_status_message(
            address=address,
            period=(min_start_ts, end_ts),
            status=TransactionStatusStep.QUERYING_TRANSACTIONS_FINISHED,
        )

    @overload
    def query_transactions_for_signatures(
            self,
            signatures: list[Signature],
            relevant_address: SolanaAddress,
            return_queried_hashes: Literal[True],
    ) -> list[Signature]:
        ...

    @overload
    def query_transactions_for_signatures(
            self,
            signatures: list[Signature],
            relevant_address: SolanaAddress,
            return_queried_hashes: Literal[False] = False,
    ) -> None:
        ...

    @overload
    def query_transactions_for_signatures(
            self,
            signatures: list[Signature],
            relevant_address: SolanaAddress,
            return_queried_hashes: bool = False,
    ) -> list[Signature] | None:
        ...

    def query_transactions_for_signatures(
            self,
            signatures: list[Signature],
            relevant_address: SolanaAddress,
            return_queried_hashes: bool = False,
    ) -> list[Signature] | None:
        """Query the transactions for the given signatures from either Helius or the RPCs,
        and save them to the DB.
        """
        solana_tx_db = DBSolanaTx(database=self.database)
        existing_sigs: set[Signature] = set()
        with self.database.conn.read_ctx() as cursor:
            existing_sigs.update(solana_tx_db.get_existing_signatures(
                cursor=cursor,
                signatures=signatures,
            ))

        # Filter out any signatures that are already in the DB. For instance, some txs are returned
        # both for the main user address and for one of its ATAs, and will have already been
        # queried when it's present here for the second address.
        filtered_signatures = [x for x in signatures if x not in existing_sigs]
        try:
            return self.helius.get_transactions(
                signatures=[str(x) for x in filtered_signatures],
                relevant_address=relevant_address,
                return_queried_hashes=return_queried_hashes,
            )
        except (RemoteError, MissingAPIKey) as e:
            log.debug(
                f'Unable to query solana transactions from Helius due to {e!s} '
                f'Falling back to querying from the RPCs for address {relevant_address}.',
            )

        queried_signatures: list[Signature] | None = [] if return_queried_hashes else None
        for chunk in get_chunks(filtered_signatures, RPC_TX_BATCH_SIZE):
            txs, token_accounts_mappings = [], {}
            for signature in chunk:
                try:
                    tx, token_accounts_mapping = self.node_inquirer.get_transaction_for_signature(signature)  # noqa: E501
                    txs.append(tx)
                    if queried_signatures is not None:
                        queried_signatures.append(tx.signature)
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
        return queried_signatures

    @overload
    def query_transactions_in_range(
            self,
            address: SolanaAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
            return_queried_hashes: Literal[True],
    ) -> list[Signature]:
        ...

    @overload
    def query_transactions_in_range(
            self,
            address: SolanaAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
            return_queried_hashes: Literal[False] = False,
    ) -> None:
        ...

    def query_transactions_in_range(
            self,
            address: SolanaAddress,
            start_ts: Timestamp,
            end_ts: Timestamp,
            return_queried_hashes: bool = False,
    ) -> list[Signature] | None:
        """Query any missing transactions for the given address and its ATAs in the given range
        and save them to the DB.

        Since solana txs can't be queried by timestamp, this uses the existing txs on either side
        of the range as the before/until parameters for the query. If these boundary txs are not
        present in the DB for one or both sides of the range, then we query all txs on that side
        to ensure we get all missed transactions for the given range.

        Returns the signatures queried in this run when requested.
        May raise RemoteError if there is a problem querying an external service.
        """
        self._send_tx_status_message(
            address=address,
            period=(start_ts, end_ts),
            status=TransactionStatusStep.QUERYING_TRANSACTIONS_STARTED,
        )

        # For each address (user address and all associated ATAs) get the signature and block
        # time for each tx within the specified range, including the next txs on either side
        # of the range to use for the before/until limits.
        txs_by_address: defaultdict[SolanaAddress, list] = defaultdict(list)
        with self.database.conn.read_ctx() as cursor:
            txs_by_address.update({SolanaAddress(x[0]): [] for x in cursor.execute(
                'SELECT ? UNION ALL SELECT ata_address FROM solana_ata_address_mappings WHERE account = ?',  # noqa: E501
                (address, address),
            )})

            for chunk, placeholders in get_query_chunks(list(txs_by_address)):
                for addr, sig, block_time in cursor.execute(
                    'SELECT sam.address as current_address, st.signature, st.block_time '
                    'FROM solana_transactions st '
                    'JOIN solanatx_address_mappings sam ON st.identifier = sam.tx_id '
                    f'WHERE sam.address IN ({placeholders}) '
                    f'AND block_time >= COALESCE(('
                    '   SELECT MAX(block_time) FROM solana_transactions st '
                    '   JOIN solanatx_address_mappings sam ON st.identifier = sam.tx_id '
                    '   WHERE sam.address = current_address AND block_time < ?'
                    '), ?) AND block_time <= COALESCE(('
                    '   SELECT MIN(block_time) FROM solana_transactions st '
                    '   JOIN solanatx_address_mappings sam ON st.identifier = sam.tx_id '
                    '   WHERE sam.address = current_address AND block_time > ?'
                    '), ?) ORDER BY sam.address, st.block_time;',
                    (*chunk, start_ts, start_ts, end_ts, end_ts),
                ):
                    txs_by_address[addr].append((sig, block_time))

        new_signatures: list[Signature] = []
        log.debug(
            f'Starting solana transaction range query for {address} from {start_ts} to {end_ts}. '
            f'Will query signatures for {len(txs_by_address)} addresses/ATAs.',
        )
        for ata_or_account, existing_txs in txs_by_address.items():
            until_sig, before_sig = None, None
            if len(existing_txs) > 0:
                first_sig, first_block_time = existing_txs[0]
                if first_block_time <= start_ts:
                    until_sig = Signature(first_sig)

                last_sig, last_block_time = existing_txs[-1]
                if last_block_time >= end_ts:
                    before_sig = Signature(last_sig)

            existing_signatures = [deserialize_tx_signature(x) for x, _ in existing_txs]
            log.debug(
                f'Querying solana signatures for {ata_or_account} belonging to {address} '
                f'in range {start_ts}-{end_ts} with before={before_sig}, until={until_sig}, '
                f'and {len(existing_signatures)} existing signatures.',
            )
            if (
                len(sigs_to_query := [x for x in self.node_inquirer.query_tx_signatures_for_address(  # noqa: E501
                    address=ata_or_account,
                    until=until_sig,
                    before=before_sig,
                ) if x not in existing_signatures]) != 0 and
                (queried_signatures := self.query_transactions_for_signatures(
                    signatures=sigs_to_query,
                    relevant_address=ata_or_account,
                    return_queried_hashes=return_queried_hashes,
                )) is not None
            ):
                new_signatures.extend(queried_signatures)
                log.debug(
                    f'Finished querying solana transactions for {ata_or_account} belonging to '
                    f'{address}. Queried {len(queried_signatures)} new signatures.',
                )
            else:
                log.debug(
                    f'No new solana transactions found for {ata_or_account} belonging to '
                    f'{address}.',
                )

        self._send_tx_status_message(
            address=address,
            period=(start_ts, end_ts),
            status=TransactionStatusStep.QUERYING_TRANSACTIONS_FINISHED,
        )
        return new_signatures if return_queried_hashes else None
