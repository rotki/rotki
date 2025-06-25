import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Literal, overload

import requests

from rotkehlchen.chain.bitcoin.constants import (
    BLOCKCHAIN_INFO_BASE_URL,
    BLOCKSTREAM_BASE_URL,
    BLOCKSTREAM_MEMPOOL_TX_PAGE_LENGTH,
    BTC_EVENT_IDENTIFIER_PREFIX,
    MEMPOOL_SPACE_BASE_URL,
)
from rotkehlchen.chain.bitcoin.types import BitcoinTx, BtcQueryAction, BtcTxIODirection
from rotkehlchen.chain.bitcoin.utils import OpCodes, pubkey_to_base58_address
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
from rotkehlchen.utils.misc import satoshis_to_btc, ts_now, ts_sec_to_ms
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

    def _query_blockstream_or_mempool_transactions(
            self,
            base_url: str,
            accounts: Sequence[BTCAddress],
            options: dict[str, Any],
    ) -> list[BitcoinTx]:
        txs, now = [], ts_now()
        for account in accounts:
            txs.extend(self._query_tx_list_from_blockstream_mempool(
                base_url=base_url,
                account=account,
                from_timestamp=options.get('from_timestamp', Timestamp(0)),
                to_timestamp=options.get('to_timestamp', now),
            ))
        return txs

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

    def _query_blockchain_info_transactions(
            self,
            accounts: Sequence[BTCAddress],
            options: dict[str, Any],
    ) -> list[BitcoinTx]:
        """Query tx list from blockchain.info and deserialize them into BitcoinTx objects.
        The txs are ordered newest to oldest from the api. The latest queried tx timestamp is
        cached and subsequent queries will stop when that timestamp is reached.

        If `to_timestamp` is set in options, any transactions newer than that will be skipped.
        This api cannot use a `from_timestamp` since the txs are returned newest to oldest.
        If we were to quit before querying to the oldest tx, the next query would stop at the
        cached latest timestamp and the skipped older txs would never be queried.

        Returns a list of deserialized BitcoinTxs.
        """
        accounts_str = ', '.join(accounts)
        log.debug(f'Querying transactions for bitcoin accounts {accounts_str} from blockchain.info')  # noqa: E501

        with self.database.conn.read_ctx() as cursor:
            latest_queried_timestamps = [
                cached_ts for account in accounts
                if (cached_ts := self.database.get_dynamic_cache(
                    cursor=cursor,
                    name=DBCacheDynamic.LAST_BITCOIN_TX_TS,
                    address=account,
                )) is not None
            ] or [Timestamp(0)]  # use zero timestamp if there are no cached timestamps

        tx_list: list[BitcoinTx] = []
        latest_queried_ts = min(latest_queried_timestamps)  # latest timestamp that all addresses are queried to.  # noqa: E501
        to_timestamp = options.get('to_timestamp', ts_now())
        for entry in self._query_blockchain_info(accounts=accounts, key='txs'):
            try:
                tx = BitcoinTx.deserialize_from_blockchain_info(entry)
            except DeserializationError as e:
                log.error(f'Failed to deserialize bitcoin transaction {entry} due to {e!s}')
                continue

            if tx.timestamp > to_timestamp:
                continue  # Haven't reached the requested range yet. Skip tx.
            if tx.timestamp <= latest_queried_ts:
                break  # All new txs have been queried - break loop, save ts to cache, and return.

            tx_list.append(tx)

        if len(tx_list) == 0:
            log.debug(f'No new transactions found for bitcoin accounts {accounts_str}')
            return []

        with self.database.conn.write_ctx() as write_cursor:
            for account in accounts:
                self.database.set_dynamic_cache(
                    write_cursor=write_cursor,
                    name=DBCacheDynamic.LAST_BITCOIN_TX_TS,
                    value=tx_list[0].timestamp,  # first in the list is the latest tx
                    address=account,
                )

        return tx_list

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
    ) -> list[BitcoinTx]:
        ...

    def _query(
            self,
            action: BtcQueryAction,
            accounts: Sequence[BTCAddress],
            options: dict[str, Any] | None = None,
    ) -> dict[BTCAddress, FVal] | dict[BTCAddress, tuple[bool, FVal]] | list[BitcoinTx]:
        """Queries bitcoin explorer APIs, if one fails the next API is tried.
        The errors from all the queries are included in the resulting remote error if all fail.

        May raise:
        - RemoteError if the queries to all the APIs fail.
        """
        errors: dict[str, str] = {}
        kwargs: dict[str, Any] = {'accounts': accounts}
        if action == BtcQueryAction.TRANSACTIONS:
            kwargs['options'] = options

        for api_name, callback in (
            ('blockchain.info', getattr(self, f'_query_blockchain_info_{action.name.lower()}')),
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
        ):
            try:
                return callback(**kwargs)
            except (
                    requests.exceptions.RequestException,
                    UnableToDecryptRemoteData,
                    requests.exceptions.Timeout,
                    RemoteError,
                    DeserializationError,
            ) as e:
                errors[api_name] = str(e)
                continue
            except KeyError as e:
                errors[api_name] = f"Got unexpected response from {api_name}. Couldn't find key {e!s}"  # noqa: E501

        serialized_errors = ', '.join(f'{source} error is: "{error}"' for (source, error) in errors.items())  # noqa: E501
        raise RemoteError(f'Bitcoin external API request failed. {serialized_errors}')

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

    def _query_tx_list_from_blockstream_mempool(
            self,
            base_url: str,
            account: BTCAddress,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
    ) -> list[BitcoinTx]:
        """Query raw bitcoin tx list from the block explorer apis and deserialize them.
        The txs are ordered newest to oldest from the api, with results automatically paginated.
        The next page is requested by specifying the last seen tx id from the previous result.
        The latest queried tx id is cached and in subsequent queries only new transactions since
        that id are queried.

        Transactions newer than `to_timestamp` will be skipped, but `from_timestamp` is currently
        ignored. Since the api returns newest to oldest, if we quit before querying to the
        oldest tx, the next query will stop at the existing cached id and the skipped older
        txs would never be queried.

        Returns a list of deserialized BitcoinTxs.
        """
        log.debug(f'Querying transactions for bitcoin account {account}')
        with self.database.conn.read_ctx() as cursor:
            last_tx_timestamp = self.database.get_dynamic_cache(
                cursor=cursor,
                name=DBCacheDynamic.LAST_BITCOIN_TX_TS,
                address=account,
            ) or Timestamp(0)

        tx_list: list[BitcoinTx] = []
        last_tx_id = ''
        while True:
            for entry in (raw_tx_list := request_get(f'{base_url}/address/{account}/txs/chain/{last_tx_id}')):  # noqa: E501
                try:
                    tx = BitcoinTx.deserialize_from_blockstream_mempool(entry)
                except DeserializationError as e:
                    log.error(f'Failed to deserialize bitcoin transaction {entry} due to {e!s}')
                    continue

                if tx.timestamp > to_timestamp:
                    continue  # Haven't reached the requested range yet. Skip tx.
                if tx.timestamp <= last_tx_timestamp:
                    return tx_list  # All new txs have been queried. Skip tx and return.

                last_tx_id = tx.tx_id
                tx_list.append(tx)

            if len(raw_tx_list) < BLOCKSTREAM_MEMPOOL_TX_PAGE_LENGTH:
                break

        if len(tx_list) == 0:
            log.debug(f'No new transactions found for bitcoin account {account}')
            return []

        with self.database.conn.write_ctx() as write_cursor:
            self.database.set_dynamic_cache(
                write_cursor=write_cursor,
                name=DBCacheDynamic.LAST_BITCOIN_TX_TS,
                value=tx_list[0].timestamp,  # first in list is latest tx
                address=account,
            )

        return tx_list

    def query_transactions(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            addresses: list[BTCAddress],
    ) -> None:
        """Query transactions in the time range for the specified accounts,
        decode them into HistoryEvents, and save the results to the db.
        """
        # TODO: websocket messages for progress updates while querying
        self.refresh_tracked_accounts()
        if len(tx_list := self._query(
            action=BtcQueryAction.TRANSACTIONS,
            accounts=addresses,
            options={'from_timestamp': from_timestamp, 'to_timestamp': to_timestamp},
        )) == 0:
            return  # no new transactions found

        events = []
        for tx in tx_list:
            events.extend(self.decode_transaction(tx))

        with self.database.conn.write_ctx() as write_cursor:
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
            len(script) > 2 and
            script[:1] == OpCodes.op_return
        ):
            return None  # not an OP_RETURN script

        # TODO: handle multiple OP_PUSHBYTES
        data_len = int.from_bytes(script[1:2])
        data = script[2:2 + data_len]

        try:  # maybe decode data as utf-8 text
            notes = f"Store text on the blockchain: {data.decode('utf-8')}"
        except (ValueError, UnicodeDecodeError):
            notes = f'Store data on the blockchain: {data.hex()}'

        return self.create_event(
            tx=tx,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            amount=ZERO,
            notes=notes,
        )

    def _maybe_derive_p2pk_address(self, raw_script: bytes) -> BTCAddress | None:
        """Attempt to derive a P2PKH address from the public key in a P2PK script.
        The script is structured as follows: OP_PUSHBYTES_X, PUBLIC_KEY_DATA, OP_CHECKSIG.
        Returns the address or None on error or if the script is not a P2PK script.
        """
        if (
            (script_len := len(raw_script)) < 1 or
            script_len < (data_len := raw_script[0]) + 2 or
            raw_script[data_len + 1:] != OpCodes.op_checksig
        ):
            return None  # not a valid p2pk script

        pubkey_bytes = raw_script[1:data_len + 1]
        try:
            return pubkey_to_base58_address(data=pubkey_bytes)
        except (ValueError, TypeError) as e:
            log.error(
                'Failed to derive p2pkh address from p2pk public key: '
                f'{pubkey_bytes.hex()} due to {e!s}',
            )
            return None

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
                if (
                    (address := tx_io.address) is None and
                    (address := self._maybe_derive_p2pk_address(tx_io.script)) is None
                ):  # Unable to find an address associated with this TxIO
                    if (event := self._maybe_decode_op_return(tx=tx, script=tx_io.script)) is not None:  # noqa: E501
                        op_return_events.append(event)
                    else:  # Unable to decode TxIO if it has no address and isn't op_return
                        log.error(f'Failed to decode {tx_io} in transaction {tx.tx_id}. Skipping.')
                else:  # address was found, add to io totals.
                    io_totals_per_address[direction][address] += tx_io.value

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
        elif in_len == 1:
            transfer_events = self._decode_single_to_many_transfers(
                tx=tx,
                single_address=next(iter(input_totals)),
                single_address_side=BtcTxIODirection.INPUT,
                other_side_totals=output_totals,
            )
        elif out_len == 1:
            transfer_events = self._decode_single_to_many_transfers(
                tx=tx,
                single_address=next(iter(output_totals)),
                single_address_side=BtcTxIODirection.OUTPUT,
                other_side_totals=input_totals,
            )
        else:
            transfer_events = self._decode_many_to_many_transfers(
                tx=tx,
                inputs=input_totals,
                outputs=output_totals,
            )

        for idx, event in enumerate(all_events := fee_events + op_return_events + transfer_events):
            event.sequence_index = idx  # assign sequence indexes in the proper order

        return all_events
