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
from rotkehlchen.chain.bitcoin.types import (
    BitcoinTx,
    BtcQueryAction,
    BtcScriptType,
    BtcTxIODirection,
)
from rotkehlchen.chain.bitcoin.utils import derive_p2pkh_from_p2pk
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError, EncodingError
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
    def _query_blockchain_info_accounts(accounts: Sequence[BTCAddress]) -> list[dict[str, Any]]:
        """Queries blockchain.info
        May raise:
        - RemoteError if got problems with querying the API
        - UnableToDecryptRemoteData if unable to load json in request_get
        - KeyError if got unexpected json structure
        """
        results: list[dict[str, Any]] = []
        accounts_chunks = [accounts[x:x + 80] for x in range(0, len(accounts), 80)]
        for accounts_chunk in accounts_chunks:
            params = '|'.join(accounts_chunk)
            btc_resp = request_get_dict(
                url=f'{BLOCKCHAIN_INFO_BASE_URL}/multiaddr?active={params}',
                handle_429=True,
                # If we get a 429 then their docs suggest 10 seconds (https://blockchain.info/q)
                backoff_in_seconds=10,
            )
            results.extend(btc_resp['addresses'])
        return results

    def _query_blockchain_info_balances(
            self,
            accounts: Sequence[BTCAddress],
    ) -> dict[BTCAddress, FVal]:
        balances: dict[BTCAddress, FVal] = {}
        for entry in self._query_blockchain_info_accounts(accounts):
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
        for entry in self._query_blockchain_info_accounts(accounts):
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
        # TODO: add support for querying the blockchain.info api for transactions as well.
        # https://www.blockchain.com/explorer/api/blockchain_api
        raise RemoteError('Currently unimplemented.')  # for the moment fall back to other api

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
            existing_tx_id = self.database.get_dynamic_cache(
                cursor=cursor,
                name=DBCacheDynamic.LAST_BITCOIN_TX_ID,
                address=account,
            )

        tx_list: list[BitcoinTx] = []
        tx_id, to_timestamp_ms = '', ts_sec_to_ms(to_timestamp)
        while True:
            for entry in (raw_tx_list := request_get(f'{base_url}/address/{account}/txs/chain/{tx_id}')):  # noqa: E501
                try:
                    tx = BitcoinTx.deserialize(entry)
                except DeserializationError as e:
                    log.error(f'Failed to deserialize bitcoin transaction {entry} due to {e!s}')
                    continue

                if tx.timestamp > to_timestamp_ms:
                    continue  # Haven't reached the requested range yet. Skip tx.
                if (tx_id := tx.tx_id) == existing_tx_id:
                    return tx_list  # All new txs have been queried. Skip tx and return.

                tx_list.append(tx)

            if len(raw_tx_list) < BLOCKSTREAM_MEMPOOL_TX_PAGE_LENGTH:
                break

        if len(tx_list) == 0:
            log.debug(f'No new transactions found for bitcoin account {account}')
            return []

        with self.database.conn.write_ctx() as write_cursor:
            self.database.set_dynamic_cache(
                write_cursor=write_cursor,
                name=DBCacheDynamic.LAST_BITCOIN_TX_ID,
                value=tx_list[0].tx_id,  # first in list is latest tx
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
            timestamp=tx.timestamp,
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

    def decode_op_return(self, tx: BitcoinTx, raw_script: str) -> HistoryEvent | None:
        """Decode an OP_RETURN script into an informational history event.
        If data is valid utf-8 encoded text, show the decoded text in the event notes.
        Returns the history event or None on error.
        """
        parts = raw_script.split()
        if not (
            len(parts) == 3 and
            parts[0] == 'OP_RETURN' and
            parts[1].startswith('OP_PUSHBYTES_')
        ):
            log.error(f'Failed to decode OP_RETURN bitcoin script "{raw_script}" in {tx.tx_id}')
            return None   # malformed OP_RETURN script

        hex_data = parts[2]
        try:  # maybe decode data as utf-8 text
            notes = f"Store text on the blockchain: {bytes.fromhex(hex_data).decode('utf-8')}"
        except (ValueError, UnicodeDecodeError):
            notes = f'Store data on the blockchain: {hex_data}'

        return self.create_event(
            tx=tx,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            amount=ZERO,
            notes=notes,
        )

    def _decode_single_input_transfers(
            self,
            tx: BitcoinTx,
            sender: BTCAddress,
            outputs: dict[BTCAddress, FVal],
    ) -> list[HistoryEvent]:
        """Decode transfers in a transaction with only one input and one or more outputs.
        Returns a list of HistoryEvents.
        """
        spend_events: list[HistoryEvent] = []
        receive_events: list[HistoryEvent] = []
        for receiver, amount in outputs.items():
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
                if tx_io.type == BtcScriptType.OP_RETURN:
                    if (event := self.decode_op_return(tx=tx, raw_script=tx_io.raw_script)) is not None:  # noqa: E501
                        op_return_events.append(event)
                    continue  # skip the rest of the checks for op_return even if no event was decoded.  # noqa: E501

                if (address := tx_io.address) is None and tx_io.type == BtcScriptType.P2PK:
                    try:  # derive the normal btc address from the raw public key used by p2pk
                        address = derive_p2pkh_from_p2pk(tx_io.pubkey)
                    except EncodingError as e:
                        log.error(f'Failed to decode P2PK bitcoin script in {tx.tx_id} {tx_io} due to {e!s}')  # noqa: E501

                if address is None:
                    log.error(f'Encountered {tx_io.type} script with no address in transaction {tx.tx_id}. Skipping.')  # noqa: E501
                    continue

                io_totals_per_address[direction][address] += tx_io.value

        # TODO: Handle when an output goes back to an input address
        #  (self transfer / btc left over from the other outputs and fee)

        fee_events, adjusted_input_totals = self._maybe_create_fee_events(
            tx=tx,
            totals_per_address=io_totals_per_address[BtcTxIODirection.INPUT],
        )

        # Get only non-zero in/out totals
        input_totals = {k: v for k, v in adjusted_input_totals.items() if v != ZERO}
        output_totals = {k: v for k, v in io_totals_per_address[BtcTxIODirection.OUTPUT].items() if v != ZERO}  # noqa: E501
        if 0 in ((in_len := len(input_totals)), (out_len := len(output_totals))):
            # Inputs have all been spent on the fee or outputs have no value (likely op_return)
            transfer_events = []  # there are no transfers
            if in_len != out_len:  # only one is zero length, either more btc is going in than came out, or vice versa  # noqa: E501
                log.error(
                    'Encountered Bitcoin transaction with mismatched '
                    'input/output amounts. Should not happen.',
                )
        else:
            transfer_events = self._decode_single_input_transfers(
                tx=tx,
                sender=next(iter(input_totals)),
                outputs=output_totals,
            ) if in_len == 1 else []  # TODO: add support for multi-input txs

        for idx, event in enumerate(all_events := fee_events + op_return_events + transfer_events):
            event.sequence_index = idx  # assign sequence indexes in the proper order

        return all_events
