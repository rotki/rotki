import logging
from collections import defaultdict
from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Literal, overload

import requests

from rotkehlchen.chain.bitcoin.constants import (
    BLOCKCHAIN_INFO_BASE_URL,
    BLOCKCYPHER_BASE_URL,
    BLOCKCYPHER_BATCH_SIZE,
    BLOCKCYPHER_TX_IO_LIMIT,
    BLOCKCYPHER_TX_LIMIT,
    BLOCKSTREAM_BASE_URL,
    BTC_EVENT_IDENTIFIER_PREFIX,
    MEMPOOL_SPACE_BASE_URL,
)
from rotkehlchen.chain.bitcoin.types import BitcoinTx, BtcQueryAction, BtcTxIODirection
from rotkehlchen.chain.bitcoin.utils import OpCodes
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.history.events.utils import decode_transfer_direction
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import ensure_type
from rotkehlchen.types import BTCAddress, Location, SupportedBlockchain, Timestamp
from rotkehlchen.utils.misc import get_chunks, satoshis_to_btc, ts_now, ts_sec_to_ms
from rotkehlchen.utils.network import request_get, request_get_dict

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class BitcoinManager:

    def __init__(
            self,
            database: 'DBHandler',
    ) -> None:
        self.database = database
        self.tracked_accounts: list[BTCAddress] = []

    def refresh_tracked_accounts(self) -> None:
        with self.database.conn.read_ctx() as cursor:
            self.tracked_accounts = self.database.get_single_blockchain_addresses(
                cursor=cursor,
                blockchain=SupportedBlockchain.BITCOIN,
            )

    @staticmethod
    def _query_blockstream_or_mempool_account_info(
            base_url: str,
            account: BTCAddress,
    ) -> tuple[FVal, int]:
        """Query account info from blockstream.info or mempool.space (APIs are nearly identical)
        Returns the account balance and tx count in a tuple.
        May raise:
        - RemoteError if got problems with querying the API
        - UnableToDecryptRemoteData if unable to load json in request_get
        - KeyError if got unexpected json structure
        - DeserializationError if got unexpected json values
        """
        response_data = request_get_dict(
            url=f'{base_url}/address/{account}',
            handle_429=True,
            backoff_in_seconds=4,
        )
        stats = response_data['chain_stats']
        funded_txo_sum = satoshis_to_btc(ensure_type(
            symbol=stats['funded_txo_sum'],
            expected_type=int,
            location='blockstream funded_txo_sum',
        ))
        spent_txo_sum = satoshis_to_btc(ensure_type(
            symbol=stats['spent_txo_sum'],
            expected_type=int,
            location='blockstream spent_txo_sum',
        ))
        return funded_txo_sum - spent_txo_sum, stats['tx_count']

    def _query_blockstream_or_mempool_balances(
            self,
            base_url: str,
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, FVal]:
        balances = {}
        for account in accounts:
            balance, _ = self._query_blockstream_or_mempool_account_info(base_url, account)
            balances[account] = balance
        return balances

    def _query_blockstream_or_mempool_has_transactions(
            self,
            base_url: str,
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, tuple[bool, FVal]]:
        have_transactions = {}
        for account in accounts:
            balance, tx_count = self._query_blockstream_or_mempool_account_info(base_url, account)
            have_transactions[account] = ((tx_count != 0), balance)
        return have_transactions

    @staticmethod
    def _query_blockchain_info(
            accounts: Sequence[BTCAddress],
            key: Literal['addresses', 'txs'] = 'addresses',
    ) -> list[dict[str, Any]]:
        """Queries blockchain.info for the specified accounts.
        The response from blockchain.info is a dict with two keys: addresses and txs, each of which
        contains a list of dicts. Returns the full list of dicts for the specified key.
        May raise:
        - RemoteError if got problems with querying the API
        - UnableToDecryptRemoteData if unable to load json in request_get
        - KeyError if got unexpected json structure
        """
        results: list[dict[str, Any]] = []
        # the docs suggest 10 seconds for 429 (https://blockchain.info/q)
        kwargs: Any = {'handle_429': True, 'backoff_in_seconds': 10}
        for i in range(0, len(accounts), 80):
            base_url = f"{BLOCKCHAIN_INFO_BASE_URL}/multiaddr?active={'|'.join(accounts[i:i + 80])}"  # noqa: E501
            if key == 'addresses':
                results.extend(request_get_dict(url=base_url, **kwargs)[key])
            else:  # key == 'txs'
                offset, limit = 0, 50
                while True:
                    results.extend(chunk := request_get_dict(
                        url=f'{base_url}&n={limit}&offset={offset}',
                        **kwargs,
                    )[key])
                    if len(chunk) < limit:
                        break  # all txs have been queried

                    offset += limit

        return results

    def _query_blockchain_info_balances(
            self,
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, FVal]:
        balances: dict[BTCAddress, FVal] = {}
        for entry in self._query_blockchain_info(accounts):
            balances[entry['address']] = satoshis_to_btc(ensure_type(
                symbol=entry['final_balance'],
                expected_type=int,
                location='blockchain.info "final_balance"',
            ))
        return balances

    def _query_blockchain_info_has_transactions(
            self,
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, tuple[bool, FVal]]:
        have_transactions = {}
        for entry in self._query_blockchain_info(accounts):
            balance = satoshis_to_btc(ensure_type(
                symbol=entry['final_balance'],
                expected_type=int,
                location='blockchain.info "final_balance"',
            ))
            have_transactions[entry['address']] = (entry['n_tx'] != 0, balance)
        return have_transactions

    def _process_raw_tx_lists(
            self,
            raw_tx_lists: list[list[dict[str, Any]]],
            options: dict[str, Any],
            processing_fn: Callable[[dict[str, Any]], BitcoinTx],
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
                    tx = processing_fn(entry)
                except (
                    DeserializationError,
                    KeyError,
                    RemoteError,
                    UnableToDecryptRemoteData,
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

    def _query_blockchain_info_transactions(
            self,
            accounts: Sequence[BTCAddress],
            options: dict[str, Any],
    ) -> tuple[int, list[BitcoinTx]]:
        """Query blockchain.info for transactions.
        Returns a tuple containing the latest queried block height and the list of txs.
        """
        return self._process_raw_tx_lists(
            raw_tx_lists=[self._query_blockchain_info(accounts=accounts, key='txs')],
            options=options,
            processing_fn=BitcoinTx.deserialize_from_blockchain_info,
        )

    def _process_raw_tx_from_blockcypher(
            self,
            data: dict[str, Any],
    ) -> BitcoinTx:
        """Convert a raw tx dict from blockcypher into a BitcoinTx.
        If the tx has a large number of TxIOs, the remaining TxIOs will be queried using the urls
        provided in the API response.
        May raise DeserializationError, KeyError, RemoteError, UnableToDecryptRemoteData.
        """
        inputs: list[dict[str, Any]] = []
        outputs: list[dict[str, Any]] = []
        for side, tx_io_list in (('inputs', inputs), ('outputs', outputs)):
            next_data = data.copy()
            while True:
                tx_io_list.extend(list_chunk := next_data[side])
                if (
                    (next_url := next_data.get(f'next_{side}')) is None or
                    len(list_chunk) < BLOCKCYPHER_TX_IO_LIMIT
                ):
                    break  # all TxIOs for this side have been queried

                next_data = request_get_dict(url=next_url, handle_429=True, backoff_in_seconds=1)

        processed_data = data.copy()  # avoid modifying the passed data dict
        processed_data['inputs'] = inputs
        processed_data['outputs'] = outputs
        return BitcoinTx.deserialize_from_blockcypher(processed_data)

    def _query_blockcypher_transactions(
            self,
            accounts: Sequence[BTCAddress],
            options: dict[str, Any],
    ) -> tuple[int, list[BitcoinTx]]:
        """Query blockcypher for transactions.
        Txs from the api are ordered newest to oldest, with pagination via block_height.
        Returns a tuple containing the latest queried block height and the list of txs.
        """
        accounts_tx_lists: dict[BTCAddress, list[dict[str, Any]]] = defaultdict(list)
        limits = f'limit={BLOCKCYPHER_TX_LIMIT}&txlimit={BLOCKCYPHER_TX_IO_LIMIT}'
        for accounts_chunk in get_chunks(list(accounts), BLOCKCYPHER_BATCH_SIZE):
            before_height = None
            while len(accounts_chunk) > 0:
                url = f"{BLOCKCYPHER_BASE_URL}/addrs/{';'.join(accounts_chunk)}/full?{limits}"
                if before_height is not None:
                    url += f'&before={before_height}'

                response = request_get(
                    url=url,
                    handle_429=True,
                    backoff_in_seconds=1,  # the free rate limit is 3 requests per second
                )
                for entry in [response] if isinstance(response, dict) else response:  # dict/list depending on single/multiple accounts  # noqa: E501
                    accounts_tx_lists[address := BTCAddress(entry['address'])].extend(txs := entry['txs'])  # noqa: E501
                    if len(txs) > 0:
                        earliest_block_height = txs[-1]['block_height']
                        before_height = (
                            earliest_block_height if before_height is None
                            else min(before_height, earliest_block_height)
                        )
                    if not entry.get('hasMore', False):
                        accounts_chunk.remove(address)

        return self._process_raw_tx_lists(
            raw_tx_lists=list(accounts_tx_lists.values()),
            options=options,
            processing_fn=self._process_raw_tx_from_blockcypher,
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
        """Queries bitcoin explorer APIs, if one fails the next API is tried.
        The errors from all the queries are included in the resulting remote error if all fail.

        * blockchain.info: Supports all actions
        * blockcypher: Currently only support for transactions is implemented.
          TODO: add support for querying blockcypher for the other actions as well.
        * blockstream.info & mempool.space: Similar APIs. Support for transactions is not
          implemented for these because they don't handle p2pk properly.

        May raise:
        - RemoteError if the queries to all the APIs fail.
        """
        errors: dict[str, str] = {}
        kwargs: dict[str, Any] = {'accounts': accounts}
        callbacks = [('blockchain.info', getattr(self, f'_query_blockchain_info_{action.name.lower()}'))]  # noqa: E501
        if action == BtcQueryAction.TRANSACTIONS:
            kwargs['options'] = options
            callbacks.append(('blockcypher.com', self._query_blockcypher_transactions))
        else:
            callbacks.extend([
                ('blockstream.info', lambda **kwargs:
                    getattr(self, f'_query_blockstream_or_mempool_{action.name.lower()}')(
                        base_url=BLOCKSTREAM_BASE_URL,
                        **kwargs,
                    ),
                 ),
                ('mempool.space', lambda **kwargs:
                    getattr(self, f'_query_blockstream_or_mempool_{action.name.lower()}')(
                        base_url=MEMPOOL_SPACE_BASE_URL,
                        **kwargs,
                    ),
                 ),
            ])

        for api_name, callback in callbacks:
            try:
                return callback(**kwargs)
            except (
                    requests.exceptions.RequestException,
                    UnableToDecryptRemoteData,
                    requests.exceptions.Timeout,
                    RemoteError,
                    DeserializationError,
                    KeyError,
            ) as e:
                msg = f'Missing key {e!s}' if isinstance(e, KeyError) else str(e)
                log.debug(f'Bitcoin external API request to {api_name} failed due to {msg}. Trying next API.')  # noqa: E501
                errors[api_name] = msg

        serialized_errors = ', '.join(f'{source} error is: "{error}"' for (source, error) in errors.items())  # noqa: E501
        raise RemoteError(f'Bitcoin external request failed for all available APIs. {serialized_errors}')  # noqa: E501

    def get_balances(self, accounts: Sequence[BTCAddress]) -> dict[BTCAddress, FVal]:
        """Queries bitcoin balances for the specified accounts.
        May raise RemoteError if the query fails.
        """
        return self._query(action=BtcQueryAction.BALANCES, accounts=accounts)

    def have_transactions(self, accounts: list[BTCAddress]) -> dict[BTCAddress, tuple[bool, FVal]]:
        """Takes a list of addresses and returns a mapping of which addresses have had transactions
        and also their current balance
        May raise RemoteError if the query fails.
        """
        return self._query(action=BtcQueryAction.HAS_TRANSACTIONS, accounts=accounts)

    def query_transactions(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            addresses: list[BTCAddress],
    ) -> None:
        """Query transactions in the time range for the specified accounts,
        decode them into HistoryEvents, and save the results to the db.

        Queries for addresses that have the same latest queried block height are batched.
        The maximum block height from any address is then saved in the cache for all addresses
        since they are all queried up to the same to_timestamp.
        """
        # TODO: websocket messages for progress updates while querying
        self.refresh_tracked_accounts()

        accounts_str = ', '.join(addresses)
        log.debug(f'Querying transactions for bitcoin accounts {accounts_str}')

        accounts_by_latest_query = defaultdict(list)
        with self.database.conn.read_ctx() as cursor:
            for address in addresses:
                block_height = self.database.get_dynamic_cache(
                    cursor=cursor,
                    name=DBCacheDynamic.LAST_BITCOIN_TX_BLOCK,
                    address=address,
                ) or 0
                accounts_by_latest_query[block_height].append(address)

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

        if len(tx_list) == 0:
            log.debug(f'No new transactions found for bitcoin accounts {accounts_str}')
            return

        events = []
        for tx in tx_list:
            events.extend(self.decode_transaction(tx))

        with self.database.conn.write_ctx() as write_cursor:
            for address in addresses:
                self.database.set_dynamic_cache(
                    write_cursor=write_cursor,
                    name=DBCacheDynamic.LAST_BITCOIN_TX_BLOCK,
                    value=new_block_height,
                    address=address,
                )

            DBHistoryEvents(self.database).add_history_events(
                write_cursor=write_cursor,
                history=events,
            )

    @staticmethod
    def create_event(
            tx: BitcoinTx,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            amount: FVal,
            notes: str | None = None,
            location_label: str | None = None,
    ) -> HistoryEvent:
        return HistoryEvent(
            event_identifier=f'{BTC_EVENT_IDENTIFIER_PREFIX}{tx.tx_id}',
            sequence_index=0,  # events are reshuffled later
            timestamp=ts_sec_to_ms(tx.timestamp),
            location=Location.BITCOIN,
            event_type=event_type,
            event_subtype=event_subtype,
            asset=A_BTC,
            amount=amount,
            notes=notes,
            location_label=location_label,
        )

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
                notes=f'Spend {fee_share} BTC for fees',
                location_label=address,
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

            event_list.append(self.create_event(
                tx=tx,
                event_type=event_type,
                event_subtype=event_subtype,
                amount=amount,
                notes=f'{verb} {amount} BTC {from_to} {address}',
                location_label=location_label,
            ))

        return spend_events + receive_events  # keep all spend events first

    def _decode_many_to_many_transfers(
            self,
            tx: BitcoinTx,
            inputs: dict[BTCAddress, FVal],
            outputs: dict[BTCAddress, FVal],
    ) -> list[HistoryEvent]:
        """Decodes transfers in a transaction with multiple inputs and multiple outputs.
        Since there's no direct mapping between specific inputs and outputs,
        we decode events as follows:
        1. Total amount sent from each input address to all outputs
        2. Total amount received by each output address from all inputs

        Note: The logic where this function is called in `decode_transaction` guarantees
        that the `inputs` and `outputs` dicts both have multiple entries.

        Returns a list of HistoryEvents.
        """
        events: list[HistoryEvent] = []
        for totals_dict, event_type, notes in (
            (inputs, HistoryEventType.SPEND, f"Send {{amount}} BTC to {', '.join(outputs.keys())}"),  # noqa: E501
            (outputs, HistoryEventType.RECEIVE, f"Receive {{amount}} BTC from {', '.join(inputs.keys())}"),  # noqa: E501
        ):
            for address, amount in totals_dict.items():
                if address not in self.tracked_accounts:
                    continue

                events.append(self.create_event(
                    tx=tx,
                    event_type=event_type,
                    event_subtype=HistoryEventSubType.NONE,
                    amount=amount,
                    notes=notes.format(amount=amount),
                    location_label=address,
                ))

        return events

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
