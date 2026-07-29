import logging
from collections import defaultdict
from typing import TYPE_CHECKING, Any, Final, Literal, overload

import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.api.websockets.typedefs import (
    TransactionStatusStep,
    TransactionStatusSubType,
    WSMessageType,
)
from rotkehlchen.chain.bitcoin.types import (
    BitcoinTx,
    BtcApiCallback,
    BtcQueryAction,
    BtcTxIODirection,
)
from rotkehlchen.chain.bitcoin.utils import OpCodes
from rotkehlchen.chain.decoding.utils import decode_transfer_direction
from rotkehlchen.chain.manager import ChainManagerWithTransactions
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.bitcointx import DBBitcoinTx
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.db.utils import get_query_chunks
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import BTCAddress, BTCTxId, Location, SupportedBlockchain, Timestamp
from rotkehlchen.utils.misc import get_chunks, ts_now, ts_sec_to_ms

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from rotkehlchen.assets.asset import Asset
    from rotkehlchen.db.cache import DBCacheDynamic
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.db.drivers.sqlite import DBCursor
    from rotkehlchen.fval import FVal

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
BITCOIN_COUNTERPARTY_ADDRESSES_METADATA_KEY = 'bitcoin_counterparty_addresses'
# Number of transactions decoded per write. Keeps a full history redecode from holding
# every event of every transaction in memory before anything is saved.
DECODING_CHUNK_SIZE: Final = 500


class BitcoinCommonManager(ChainManagerWithTransactions[BTCAddress]):

    def __init__(
            self,
            database: DBHandler,
            blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
            asset: Asset,
            group_identifier_prefix: str,
            cache_key: Literal[DBCacheDynamic.LAST_BTC_TX_BLOCK, DBCacheDynamic.LAST_BCH_TX_BLOCK],
            api_callbacks: list[BtcApiCallback],
    ) -> None:
        """Common class for the bitcoin and bitcoin cash managers."""
        self.database = database
        self.tracked_accounts: list[BTCAddress] = []
        self.blockchain = blockchain
        self.location = Location.from_chain(self.blockchain)
        self.asset = asset
        self.group_identifier_prefix = group_identifier_prefix
        self.cache_key = cache_key
        self.api_callbacks = api_callbacks
        self.dbtx = DBBitcoinTx(database)

    def refresh_tracked_accounts(self) -> None:
        with self.database.conn.read_ctx() as cursor:
            self.tracked_accounts = self.database.get_single_blockchain_addresses(
                cursor=cursor,
                blockchain=self.blockchain,
            )

    def get_display_address(self, address: BTCAddress) -> BTCAddress:
        """Returns the display address for the given address.
        Reimplemented in subclasses to return the address in a different format.
        """
        return address

    def get_api_address(self, address: BTCAddress) -> BTCAddress:
        """Returns the address in the format the APIs use, which is what TxIOs are saved
        with. The inverse of get_display_address, resolved via the tracked accounts since
        the conversion the subclasses do only goes one way.
        """
        return next(
            (x for x in self.tracked_accounts if self.get_display_address(x) == address),
            address,
        )

    @overload
    def _query(
            self,
            action: Literal[BtcQueryAction.BALANCES],
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, FVal]:
        ...

    @overload
    def _query(
            self,
            action: Literal[BtcQueryAction.HAS_TRANSACTIONS],
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, tuple[bool, FVal]]:
        ...

    @overload
    def _query(
            self,
            action: Literal[BtcQueryAction.TRANSACTIONS],
            accounts: Sequence[BTCAddress],
            options: dict[str, Any],
    ) -> tuple[int, list[BitcoinTx]]:
        ...

    def _query(
            self,
            action: BtcQueryAction,
            accounts: Sequence[BTCAddress],
            options: dict[str, Any] | None = None,
    ) -> dict[BTCAddress, FVal] | dict[BTCAddress, tuple[bool, FVal]] | tuple[int, list[BitcoinTx]]:  # noqa: E501
        """Queries explorer APIs for the specified action as defined in `self.api_callbacks`.
        If one query fails the next API for that action is tried, and the errors from all the
        queries are included in the resulting remote error if all fail.

        May raise:
        - RemoteError if the queries to all the APIs fail.
        """
        errors: dict[str, str] = {}
        for callback in self.api_callbacks:
            log.debug(f'Querying {callback.name} for {self.blockchain} address balances')
            try:
                if action == BtcQueryAction.BALANCES and callback.balances_fn is not None:
                    return callback.balances_fn(accounts)
                if action == BtcQueryAction.HAS_TRANSACTIONS and callback.has_transactions_fn is not None:  # noqa: E501
                    return callback.has_transactions_fn(accounts)
                if action == BtcQueryAction.TRANSACTIONS and callback.transactions_fn is not None:
                    return callback.transactions_fn(accounts, options)  # type: ignore[arg-type] # overloads ensure options will not be None for txs
                # else skip to the next api if the function for this action is not implemented
                continue
            except (
                    requests.exceptions.RequestException,
                    UnableToDecryptRemoteData,
                    requests.exceptions.Timeout,
                    RemoteError,
                    DeserializationError,
                    KeyError,
            ) as e:
                msg = f'Missing key {e!s}' if isinstance(e, KeyError) else str(e)
                log.debug(f'External {self.blockchain!s} API request to {callback.name} failed due to {msg}. Trying next API.')  # noqa: E501
                errors[callback.name] = msg

        serialized_errors = ', '.join(f'{source} error is: "{error}"' for (source, error) in errors.items())  # noqa: E501
        raise RemoteError(f'External {self.blockchain!s} request failed for all available APIs. {serialized_errors}')  # noqa: E501

    def query_balances(self, addresses: Sequence[BTCAddress]) -> dict[BTCAddress, Balance]:
        """Queries bitcoin balances for the specified accounts.
        May raise RemoteError if the query fails.
        """
        balances = {}
        btc_price = Inquirer.find_main_currency_price(self.asset)
        for account, balance in self._query(
                action=BtcQueryAction.BALANCES,
                accounts=addresses,
        ).items():
            balances[account] = Balance(
                amount=balance,
                value=balance * btc_price,
            )

        return balances

    def have_transactions(self, accounts: list[BTCAddress]) -> dict[BTCAddress, tuple[bool, FVal]]:
        """Takes a list of addresses and returns a mapping of which addresses have had transactions
        and also their current balance
        May raise RemoteError if the query fails.
        """
        return self._query(action=BtcQueryAction.HAS_TRANSACTIONS, accounts=accounts)

    def _send_tx_ws_status(
            self,
            addresses: list[BTCAddress],
            status: TransactionStatusStep,
    ) -> None:
        """Send tx querying status WS message to the frontend."""
        self.database.msg_aggregator.add_message(
            message_type=WSMessageType.TRANSACTION_STATUS,
            data={
                'addresses': addresses,
                'chain': self.blockchain.value,
                'subtype': str(TransactionStatusSubType.BITCOIN),
                'status': str(status),
            },
        )

    def query_transactions(
            self,
            addresses: list[BTCAddress],
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> None:
        """Query transactions in the time range for the specified accounts,
        decode them into HistoryEvents, and save the results to the db.

        Queries for addresses that have the same latest queried block height are batched.
        The maximum block height from any address is then saved in the cache for all addresses
        since they are all queried up to the same to_timestamp.
        """
        self._send_tx_ws_status(
            addresses=addresses,
            status=TransactionStatusStep.QUERYING_TRANSACTIONS_STARTED,
        )
        self.refresh_tracked_accounts()

        accounts_str = ', '.join(addresses)
        log.debug(f'Querying transactions for {self.blockchain!s} accounts {accounts_str}')

        accounts_by_latest_query = defaultdict(list)
        with self.database.conn.read_ctx() as cursor:
            for address in addresses:
                block_height = self.database.get_dynamic_cache(
                    cursor=cursor,
                    name=self.cache_key,
                    address=address,
                ) or 0
                accounts_by_latest_query[block_height].append(address)

        # An address queried for the first time may already appear in transactions saved for
        # another address. Those were decoded while it was untracked, so their events are
        # outdated. Mark them now and they get decoded again along with the new ones.
        if len(new_addresses := accounts_by_latest_query.get(0, [])) != 0:
            self.mark_addresses_transactions_for_redecode(new_addresses)

        tx_list: list[BitcoinTx] = []
        new_block_height = 0
        for last_queried_block, accounts in accounts_by_latest_query.items():
            block_height, accounts_txs = self._query(
                action=BtcQueryAction.TRANSACTIONS,
                accounts=accounts,
                options={'to_timestamp': to_timestamp, 'last_queried_block': last_queried_block},
            )
            if len(accounts_txs) == 0:
                new_block_height = max(new_block_height, last_queried_block)
                continue

            new_block_height = max(new_block_height, block_height)
            tx_list.extend(accounts_txs)

        self._send_tx_ws_status(
            addresses=addresses,
            status=TransactionStatusStep.QUERYING_TRANSACTIONS_FINISHED,
        )
        if len(tx_list) == 0:
            log.debug(f'No new transactions found for {self.blockchain!s} accounts {accounts_str}')
            return

        unique_txs = {tx.tx_id: tx for tx in tx_list}  # the same tx is returned once per queried address it touches  # noqa: E501
        with self.database.conn.write_ctx() as write_cursor:
            for address in addresses:
                self.database.set_dynamic_cache(
                    write_cursor=write_cursor,
                    name=self.cache_key,
                    value=new_block_height,
                    address=address,
                )

            # Save the transactions before decoding them. Decoding runs in its own write so
            # that a failure only leaves them pending decoding instead of losing the query.
            self._save_transactions(
                write_cursor=write_cursor,
                transactions=list(unique_txs.values()),
            )

        self._send_tx_ws_status(
            addresses=addresses,
            status=TransactionStatusStep.DECODING_TRANSACTIONS_STARTED,
        )
        self.decode_transactions()
        self._send_tx_ws_status(
            addresses=addresses,
            status=TransactionStatusStep.DECODING_TRANSACTIONS_FINISHED,
        )

    def _save_transactions(
            self,
            write_cursor: DBCursor,
            transactions: list[BitcoinTx],
    ) -> None:
        """Save the given transactions, associating each with the tracked addresses that
        take part in it. The addresses are saved in the format they are tracked in, which
        for bitcoin cash is not the one the APIs return them in.
        """
        for tx in transactions:
            if len(relevant_addresses := {
                self.get_display_address(tx_io.address)
                for tx_io in tx.inputs + tx.outputs
                if tx_io.address is not None and tx_io.address in self.tracked_accounts
            }) == 0:
                log.error(
                    'Found %s transaction %s without any tracked address in its inputs '
                    'or outputs. Should not happen.',
                    self.blockchain,
                    tx.tx_id,
                )

            self.dbtx.add_transactions(  # one at a time since the addresses differ per tx
                write_cursor=write_cursor,
                transactions=[tx],
                location=self.location,
                relevant_addresses=list(relevant_addresses),
            )

    def decode_transactions(self, tx_ids: list[BTCTxId] | None = None) -> int:
        """Decode the saved transactions that are pending decoding into history events.

        If tx_ids is given only those transactions are considered. Returns the number of
        transactions decoded.
        """
        self.refresh_tracked_accounts()
        with self.database.conn.read_ctx() as cursor:
            transactions = self.dbtx.get_transactions(
                cursor=cursor,
                location=self.location,
                tx_ids=tx_ids,
                undecoded_only=True,
            )

        if len(transactions) == 0:
            return 0

        dbevents = DBHistoryEvents(self.database)
        for tx_chunk in get_chunks(transactions, DECODING_CHUNK_SIZE):
            events, decoded_tx_ids = [], set()
            for tx in tx_chunk:
                decoded_tx_ids.add(BTCTxId(tx.tx_id))
                events.extend(self.decode_transaction(tx))

            with self.database.conn.write_ctx() as write_cursor:
                # Replace any previously decoded events for these transactions. Sequence
                # indexes are positional, so when the tracked account set changed since the
                # last decode (e.g. an xpub was added after a standalone address) the new
                # events collide with the stale ones under
                # UNIQUE(group_identifier, sequence_index). Inserting without purging first
                # keeps outdated rows and silently drops the corrected ones.
                dbevents.delete_events_by_tx_ref(
                    write_cursor=write_cursor,
                    tx_refs=list(decoded_tx_ids),
                    location=self.location,
                    customized_handling='preserve_transactions',
                )
                if len(customized := self._get_customized_group_identifiers(
                    cursor=write_cursor,
                    tx_ids=decoded_tx_ids,
                )) != 0:  # these were kept above, so don't try to write over them
                    events = [x for x in events if x.group_identifier not in customized]

                dbevents.add_history_events(write_cursor=write_cursor, history=events)
                self.dbtx.set_decoded(
                    write_cursor=write_cursor,
                    location=self.location,
                    tx_ids=list(decoded_tx_ids),
                )

        return len(transactions)

    def redecode_transactions(self, tx_ids: list[BTCTxId] | None = None) -> int:
        """Decode the saved transactions again, replacing their existing events.
        If tx_ids is given only those transactions are redecoded, otherwise all of them.

        Since the raw transactions are saved locally this needs no querying of the
        explorers, which is what makes it usable to correct a decoding mistake.
        """
        with self.database.conn.write_ctx() as write_cursor:
            self.dbtx.reset_decoded_state(
                write_cursor=write_cursor,
                location=self.location,
                tx_ids=tx_ids,
            )

        return self.decode_transactions(tx_ids=tx_ids)

    def mark_addresses_transactions_for_redecode(self, addresses: list[BTCAddress]) -> None:
        """Mark the saved transactions the given addresses take part in as pending decoding.

        The events of a bitcoin transaction depend on which of its addresses are tracked, so
        a transaction that was decoded while one of these was untracked is now outdated. It
        needs no querying since the transactions are already saved.
        """
        with self.database.conn.write_ctx() as write_cursor:
            tx_ids: set[BTCTxId] = set()
            for address in addresses:
                tx_ids.update(self.dbtx.get_transaction_ids_for_address(
                    cursor=write_cursor,
                    location=self.location,
                    address=self.get_api_address(address),
                ))

            if len(tx_ids) == 0:
                return

            log.debug(
                'Marking %s %s transactions of %s newly tracked addresses for redecoding',
                len(tx_ids),
                self.blockchain,
                len(addresses),
            )
            self.dbtx.reset_decoded_state(
                write_cursor=write_cursor,
                location=self.location,
                tx_ids=list(tx_ids),
            )

    def _get_customized_group_identifiers(
            self,
            cursor: DBCursor,
            tx_ids: set[BTCTxId],
    ) -> set[str]:
        """Get the group identifiers of the given txs that still have events in the DB.
        Only called right after purging their events, so anything still present was
        deliberately preserved for containing a customized event.

        Chunked since a full history redecode passes every tx of every queried address.
        """
        customized: set[str] = set()
        for chunk, placeholders in get_query_chunks(
            data=[f'{self.group_identifier_prefix}{tx_id}' for tx_id in tx_ids],
        ):
            customized.update(
                row[0] for row in cursor.execute(
                    f'SELECT DISTINCT group_identifier FROM history_events '
                    f'WHERE group_identifier IN ({placeholders})',
                    chunk,
                )
            )

        return customized

    def _process_raw_tx_lists(
            self,
            raw_tx_lists: list[list[dict[str, Any]]],
            options: dict[str, Any],
            processing_fn: Callable[[dict[str, Any]], BitcoinTx | None],
    ) -> tuple[int, list[BitcoinTx]]:
        """Convert raw txs into BitcoinTxs using the specified deserialize_fn.
        The tx lists must be ordered newest to oldest (the order used by the current APIs).

        If `queried_block_height` is set in options, deserialization will stop when that
        block height is reached.

        If `to_timestamp` is set in options, any transactions newer than that will be skipped.
        But we cannot use a `from_timestamp` since the txs are returned newest to oldest.
        If we were to quit before querying to the oldest tx, the next query would stop at the
        cached queried_block_height and the skipped older txs would never be queried.

        Returns the latest queried block height (cached and referenced in subsequent queries)
        and the list of deserialized BitcoinTxs in a tuple.
        """
        tx_list: list[BitcoinTx] = []
        last_queried_block = options.get('last_queried_block', 0)
        to_timestamp = options.get('to_timestamp', ts_now())
        new_block_height = 0
        for raw_tx_list in raw_tx_lists:
            for entry in raw_tx_list:
                try:
                    if (tx := processing_fn(entry)) is None:
                        log.debug(f'Skipping unconfirmed bitcoin transaction {entry}')
                        continue
                except (
                    DeserializationError,  # malformed data encountered when deserializing entry
                    KeyError,  # missing required key when deserializing entry
                    ValueError,  # bad value in bytes.fromhex() when deserializing TxIO scripts
                    RemoteError,  # failure to query remote (_process_raw_tx_from_blockcypher queries more TxIOs if the initial data is incomplete)  # noqa: E501
                    UnableToDecryptRemoteData,  # malformed data from remote
                ) as e:
                    msg = f'Missing key {e!s}' if isinstance(e, KeyError) else str(e)
                    log.error(f'Failed to process bitcoin transaction {entry} due to {msg}')
                    continue

                if tx.timestamp > to_timestamp:
                    continue  # Haven't reached the requested range yet. Skip tx.

                if tx.block_height <= last_queried_block:
                    break  # All new txs have been queried. Skip tx and return.

                tx_list.append(tx)

            block_height = tx_list[0].block_height if len(tx_list) > 0 else last_queried_block
            new_block_height = max(new_block_height, block_height)

        return new_block_height, tx_list

    def create_event(
            self,
            tx: BitcoinTx,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            amount: FVal,
            notes: str | None = None,
            location_label: str | None = None,
            counterparty_addresses: list[BTCAddress] | None = None,
    ) -> HistoryEvent:
        event = HistoryEvent(
            group_identifier=f'{self.group_identifier_prefix}{tx.tx_id}',
            sequence_index=0,  # events are reshuffled later
            timestamp=ts_sec_to_ms(tx.timestamp),
            location=self.location,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=self.asset,
            amount=amount,
            notes=notes,
            location_label=self.get_display_address(BTCAddress(location_label)) if location_label is not None else None,  # noqa: E501
        )
        if counterparty_addresses is not None:
            setattr(
                event,
                BITCOIN_COUNTERPARTY_ADDRESSES_METADATA_KEY,
                [str(self.get_display_address(address)) for address in counterparty_addresses],
            )
        return event

    def _maybe_create_fee_events(
            self,
            tx: BitcoinTx,
            totals_per_address: dict[BTCAddress, FVal],
    ) -> tuple[list[HistoryEvent], dict[BTCAddress, FVal]]:
        """Create fee events for inputs from tracked addresses.
        Fee amount per address is proportional to the amount spent by that address.
        The fee share for each address is subtracted from the total input for that address.
        Returns the list of fee events and the adjusted input totals in a tuple.
        """
        events: list[HistoryEvent] = []
        if tx.fee == ZERO:  # Some early txs have no fee
            return events, totals_per_address

        if (total_input := sum(totals_per_address.values())) == ZERO:  # Prevent division by zero when calculating fee share.  # noqa: E501
            log.error('Encountered btc transaction with zero input value. Should not happen.')
            return events, totals_per_address

        remaining_fee = tx.fee  # Track remaining fee to ensure entire fee amount is accounted for.
        for idx, (address, amount) in enumerate(totals_per_address.items()):
            # Calculate the fee share and subtract it from the totals even for untracked accounts,
            # since all the totals may need to be referenced in subsequent decoding logic.
            if idx == len(totals_per_address) - 1:
                fee_share = remaining_fee  # Last address absorbs residual from any rounding errors in the share calculation.  # noqa: E501
            else:
                fee_share = (amount / total_input) * tx.fee
                remaining_fee -= fee_share

            totals_per_address[address] -= fee_share
            if address not in self.tracked_accounts:
                continue  # only add the fee event for tracked accounts

            events.append(self.create_event(
                tx=tx,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                amount=fee_share,
                notes=f'Spend {fee_share} {self.asset.identifier} for fees',
                location_label=self.get_display_address(address),
            ))

        return events, totals_per_address

    def _handle_self_transfers(
            self,
            input_totals: dict[BTCAddress, FVal],
            output_totals: dict[BTCAddress, FVal],
    ) -> tuple[dict[BTCAddress, FVal], dict[BTCAddress, FVal]]:
        """Handles any transfers that go back to the same address.
        Subtracts any self transfer amounts from the input and output totals.
        Returns a tuple containing the adjusted inputs and the adjusted outputs.
        """
        # Loop over addresses that appear in both inputs and outputs
        for address in set(input_totals.keys()) & set(output_totals.keys()):
            if (input_amount := input_totals[address]) > (output_amount := output_totals[address]):
                input_totals[address] -= output_amount
                output_totals.pop(address)
            elif output_amount > input_amount:
                input_totals.pop(address)
                output_totals[address] -= input_amount
            else:  # output_amount == input_amount
                input_totals.pop(address)
                output_totals.pop(address)

        return input_totals, output_totals

    def _maybe_decode_op_return(self, tx: BitcoinTx, script: bytes) -> HistoryEvent | None:
        """Decode an OP_RETURN script into an informational history event.
        If data is valid utf-8 encoded text, show the decoded text in the event notes.
        Returns the history event or None on error.
        """
        if not (
            (script_len := len(script)) >= 2 and
            script[:1] == OpCodes.OP_RETURN
        ):
            return None  # not an OP_RETURN script

        data_chunks, position = [], 1
        while position < script_len:
            push_opcode = script[position:position + 1]  # Use slice instead of index to avoid converting op code to int.  # noqa: E501
            position += 1  # increment for push opcode byte
            data_len = length_bytes = 0
            if 1 <= (push_int := int.from_bytes(push_opcode)) <= 75:  # OP_PUSHBYTES_1 to OP_PUSHBYTES_75  # noqa: E501
                data_len = push_int
            elif push_opcode == OpCodes.OP_PUSHDATA1:
                length_bytes = 1
            elif push_opcode == OpCodes.OP_PUSHDATA2:
                length_bytes = 2
            elif push_opcode == OpCodes.OP_PUSHDATA4:
                length_bytes = 4
            elif push_opcode == OpCodes.OP_0:
                data_chunks.append(b'\x00')
                continue
            elif 1 <= (push_int := int.from_bytes(push_opcode) - 80) <= 16:  # OP_1 to OP_16
                data_chunks.append(push_int.to_bytes())
                continue

            if length_bytes > 0 and position + length_bytes < script_len:
                data_len = int.from_bytes(script[position:position + length_bytes])
                position += length_bytes

            if data_len == 0 or position + data_len > script_len:
                log.error(f'Malformed OP_RETURN script {script.hex()} in tx {tx.tx_id}')
                break

            data_chunks.append(script[position:position + data_len])
            position += data_len

        if len(data_chunks) == 0:
            log.error(f'Failed to find any data in OP_RETURN script {script.hex()} in tx {tx.tx_id}')  # noqa: E501
            return None

        data = b''.join(data_chunks)
        try:  # maybe decode data as utf-8 text
            decoded_text = data.decode('utf-8').strip('\x00')  # Text may be padded with null bytes in some cases.  # noqa: E501
            notes = f'Store text on the blockchain: {decoded_text}'
        except (ValueError, UnicodeDecodeError):
            notes = f'Store data on the blockchain: {data.hex()}'

        return self.create_event(
            tx=tx,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            amount=ZERO,
            notes=notes,
        )

    def _decode_single_to_many_transfers(
            self,
            tx: BitcoinTx,
            single_address: BTCAddress,
            single_address_side: BtcTxIODirection,
            other_side_totals: dict[BTCAddress, FVal],
    ) -> list[HistoryEvent]:
        """Decode transfers in a transaction with one side only having a single address and
        the other side having one or more addresses.
        Returns a list of HistoryEvents.
        """
        spend_events: list[HistoryEvent] = []
        receive_events: list[HistoryEvent] = []
        get_sender_receiver = (  # to avoid repeating the if check in every loop iteration
            (lambda addr: (single_address, addr))
            if single_address_side == BtcTxIODirection.INPUT else
            (lambda addr: (addr, single_address))
        )
        for other_side_address, amount in other_side_totals.items():
            sender, receiver = get_sender_receiver(other_side_address)
            direction_result = decode_transfer_direction(
                from_address=sender,
                to_address=receiver,
                tracked_accounts=self.tracked_accounts,
                maybe_get_exchange_fn=lambda _: None,
            )
            if direction_result is None:
                continue  # skip outputs to untracked addresses when sender also isn't tracked

            event_type, event_subtype, location_label, address, _, verb = direction_result
            if event_type == HistoryEventType.RECEIVE:
                event_list = receive_events
                from_to = 'from'
            else:  # SPEND or TRANSFER
                event_list = spend_events
                from_to = 'to'

            suffix, counterparty_addresses = (
                (f' {from_to} {self.get_display_address(address)}', [address])
                if address is not None else ('', None)
            )
            event_list.append(self.create_event(
                tx=tx,
                event_type=event_type,
                event_subtype=event_subtype,
                amount=amount,
                notes=f'{verb} {amount} {self.asset.identifier}{suffix}',
                location_label=location_label,
                counterparty_addresses=counterparty_addresses,
            ))

        return spend_events + receive_events  # keep all spend events first

    def _decode_many_to_many_transfers(
            self,
            tx: BitcoinTx,
            inputs: dict[BTCAddress, FVal],
            outputs: dict[BTCAddress, FVal],
    ) -> list[HistoryEvent]:
        """Decodes transfers in a transaction with multiple inputs and multiple outputs.
        Since there's no direct mapping between specific inputs and outputs, each address'
        amount is split across the opposite side proportionally to that side's totals.

        The split is done per tracked/untracked side so that value staying inside the wallet
        (most commonly a change output) is decoded as a TRANSFER rather than as a
        SPEND/RECEIVE pair. Emitting the latter would report a disposal and an acquisition
        that never happened, corrupting cost basis even though the net balance is unaffected.
        This mirrors what `_decode_single_to_many_transfers` already does via
        `decode_transfer_direction`.

        Note: The logic where this function is called in `decode_transaction` guarantees
        that the `inputs` and `outputs` dicts both have multiple entries, and that all the
        amounts in them are non-zero.

        Note: when `tx.multi_io` is set the API may have omitted TxIOs unrelated to the
        queried addresses, so the totals below can be incomplete. Each address' own amount is
        still fully allocated, but the tracked/untracked proportions are only as good as the
        data the API returned.

        Returns a list of HistoryEvents.
        """
        tracked_inputs, external_inputs = self._split_by_tracked(inputs)
        tracked_outputs, external_outputs = self._split_by_tracked(outputs)
        total_input, total_output = sum(inputs.values()), sum(outputs.values())
        external_output_total = sum(external_outputs.values())
        external_input_total = sum(external_inputs.values())

        spend_events: list[HistoryEvent] = []
        transfer_events: list[HistoryEvent] = []
        receive_events: list[HistoryEvent] = []
        for address, amount in tracked_inputs.items():
            if external_output_total != ZERO:  # the part that actually leaves the wallet
                spend_events.append(self.create_event(
                    tx=tx,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.NONE,
                    amount=(spend_amount := amount * external_output_total / total_output),
                    notes=f'Send {spend_amount} {self.asset.identifier} to {self._display_addresses(external_outputs)}',  # noqa: E501
                    location_label=address,
                    counterparty_addresses=list(external_outputs),
                ))

            # The part staying in the wallet. One event per receiving address so that the
            # per-address balance buckets get an exact counterparty to credit.
            for output_address, output_amount in tracked_outputs.items():
                transfer_events.append(self.create_event(
                    tx=tx,
                    event_type=HistoryEventType.TRANSFER,
                    event_subtype=HistoryEventSubType.NONE,
                    amount=(transfer_amount := amount * output_amount / total_output),
                    notes=f'Transfer {transfer_amount} {self.asset.identifier} to {self.get_display_address(output_address)}',  # noqa: E501
                    location_label=address,
                    counterparty_addresses=[output_address],
                ))

        if external_input_total != ZERO:  # the part actually entering the wallet
            for address, amount in tracked_outputs.items():
                receive_events.append(self.create_event(
                    tx=tx,
                    event_type=HistoryEventType.RECEIVE,
                    event_subtype=HistoryEventSubType.NONE,
                    amount=(receive_amount := amount * external_input_total / total_input),
                    notes=f'Receive {receive_amount} {self.asset.identifier} from {self._display_addresses(external_inputs)}',  # noqa: E501
                    location_label=address,
                    counterparty_addresses=list(external_inputs),
                ))

        return spend_events + transfer_events + receive_events

    def _split_by_tracked(
            self,
            totals: dict[BTCAddress, FVal],
    ) -> tuple[dict[BTCAddress, FVal], dict[BTCAddress, FVal]]:
        """Split the given address totals into tracked and untracked ones."""
        tracked, untracked = {}, {}
        for address, amount in totals.items():
            if address in self.tracked_accounts:
                tracked[address] = amount
            else:
                untracked[address] = amount

        return tracked, untracked

    def _display_addresses(self, addresses: dict[BTCAddress, FVal]) -> str:
        return ', '.join([self.get_display_address(x) for x in addresses])

    def decode_transaction(self, tx: BitcoinTx) -> list[HistoryEvent]:
        """Decode a BitcoinTx into HistoryEvents.
        Combines multiple inputs/outputs per address into single events with total amounts.
        Creates fee events proportional to the total amount spent by each address.
        Returns a list of HistoryEvents.
        """
        op_return_events = []
        io_totals_per_address: dict[BtcTxIODirection, dict[BTCAddress, FVal]] = {
            BtcTxIODirection.INPUT: defaultdict(lambda: ZERO),
            BtcTxIODirection.OUTPUT: defaultdict(lambda: ZERO),
        }
        for tx_io_list, direction in (
            (tx.inputs, BtcTxIODirection.INPUT),
            (tx.outputs, BtcTxIODirection.OUTPUT),
        ):
            for tx_io in tx_io_list:
                if (address := tx_io.address) is not None:
                    io_totals_per_address[direction][address] += tx_io.value
                elif (  # decode op_return if an input is tracked and the script is present.
                    tx_io.script is not None and
                    any(tx_input.address in self.tracked_accounts for tx_input in tx.inputs) and
                    (event := self._maybe_decode_op_return(tx=tx, script=tx_io.script)) is not None
                ):
                    op_return_events.append(event)
                else:  # Unable to decode TxIO if it has no address and isn't op_return
                    log.error(f'Failed to decode {tx_io} in transaction {tx.tx_id}. Skipping.')

        # Handle self transfers before fees to avoid including self transfer amounts
        # when calculating the proportional fee shares.
        adjusted_inputs, adjusted_outputs = self._handle_self_transfers(
            input_totals=io_totals_per_address[BtcTxIODirection.INPUT],
            output_totals=io_totals_per_address[BtcTxIODirection.OUTPUT],
        )
        fee_events, adjusted_inputs = self._maybe_create_fee_events(
            tx=tx,
            totals_per_address=adjusted_inputs,
        )

        # Get only non-zero in/out totals
        input_totals = {k: v for k, v in adjusted_inputs.items() if v != ZERO}
        output_totals = {k: v for k, v in adjusted_outputs.items() if v != ZERO}
        if 0 in ((in_len := len(input_totals)), (out_len := len(output_totals))):
            # Inputs have all been spent on the fee or outputs have no value (likely op_return)
            transfer_events = []  # there are no transfers
            if in_len != out_len:  # only one is zero length, either more btc is going in than came out, or vice versa  # noqa: E501
                log.error(
                    'Encountered Bitcoin transaction with mismatched '
                    'input/output amounts. Should not happen.',
                )
        elif tx.multi_io or (in_len > 1 and out_len > 1):
            # if multi_io is set process it as a many-to-many even if fewer TxIOs are present.
            # this ensures correct decoding when blockchain.info omits unrelated TxIOs.
            transfer_events = self._decode_many_to_many_transfers(
                tx=tx,
                inputs=input_totals,
                outputs=output_totals,
            )
        elif in_len == 1:
            transfer_events = self._decode_single_to_many_transfers(
                tx=tx,
                single_address=next(iter(input_totals)),
                single_address_side=BtcTxIODirection.INPUT,
                other_side_totals=output_totals,
            )
        else:  # out_len == 1
            transfer_events = self._decode_single_to_many_transfers(
                tx=tx,
                single_address=next(iter(output_totals)),
                single_address_side=BtcTxIODirection.OUTPUT,
                other_side_totals=input_totals,
            )

        for idx, event in enumerate(all_events := fee_events + op_return_events + transfer_events):
            event.sequence_index = idx  # assign sequence indexes in the proper order

        return all_events
