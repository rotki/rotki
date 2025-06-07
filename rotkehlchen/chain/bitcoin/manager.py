import logging
from collections import defaultdict
from collections.abc import Sequence
from typing import TYPE_CHECKING

from rotkehlchen.chain.bitcoin.constants import BLOCKSTREAM_BASE_URL, MEMPOOL_SPACE_BASE_URL
from rotkehlchen.chain.bitcoin.types import BitcoinTx, BtcScriptType
from rotkehlchen.chain.bitcoin.utils import query_apis_via_callbacks, query_blockstream_or_mempool_api, \
    derive_p2pkh_from_p2pk
from rotkehlchen.constants.assets import A_BTC
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.db.cache import DBCacheDynamic
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.types import HistoryEventType, HistoryEventSubType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import ensure_type
from rotkehlchen.types import BTCAddress, Timestamp, Location, SupportedBlockchain
from rotkehlchen.utils.misc import satoshis_to_btc, ts_sec_to_ms
from rotkehlchen.utils.network import request_get_dict, request_get

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def _query_blockstream_or_mempool_balances(
        accounts: Sequence[BTCAddress],
        base_url: str,
) -> dict[BTCAddress, FVal]:
    """Queries balances from blockstream.info
    May raise:
    - RemoteError if got problems with querying the API
    - KeyError if got unexpected json structure
    - DeserializationError if got unexpected json values
    """
    balances = {}
    for account in accounts:
        url = f'{base_url}/address/{account}'
        response_data = request_get_dict(url=url, handle_429=True, backoff_in_seconds=4)
        stats = response_data['chain_stats']
        funded_txo_sum = satoshis_to_btc(
            ensure_type(
                symbol=stats['funded_txo_sum'],
                expected_type=int,
                location='blockstream funded_txo_sum',
            ),
        )
        spent_txo_sum = satoshis_to_btc(
            ensure_type(
                symbol=stats['spent_txo_sum'],
                expected_type=int,
                location='blockstream spent_txo_sum',
            ),
        )
        balance = funded_txo_sum - spent_txo_sum
        balances[account] = balance
    return balances


def _query_blockchain_info_balances(accounts: Sequence[BTCAddress]) -> dict[BTCAddress, FVal]:
    """Queries balances from blockchain.info
    May raise:
    - RemoteError if got problems with querying the API
    - KeyError if got unexpected json structure
    - DeserializationError if got unexpected json values
    """
    balances: dict[BTCAddress, FVal] = {}
    accounts_chunks = [accounts[x:x + 80] for x in range(0, len(accounts), 80)]
    for accounts_chunk in accounts_chunks:
        params = '|'.join(accounts_chunk)
        btc_resp = request_get_dict(
            url=f'https://blockchain.info/multiaddr?active={params}',
            handle_429=True,
            # If we get a 429 then their docs suggest 10 seconds
            # https://blockchain.info/q
            backoff_in_seconds=10,
        )
        for entry in btc_resp['addresses']:
            balances[entry['address']] = satoshis_to_btc(
                ensure_type(
                    symbol=entry['final_balance'],
                    expected_type=int,
                    location='blockchain.info "final_balance"',
                ),
            )
    return balances


class BitcoinManager:

    def __init__(
            self,
            database: 'DBHandler',
    ) -> None:
        self.database = database
        self.tracked_accounts = []

    def refresh_tracked_accounts(self):
        with self.database.conn.read_ctx() as cursor:
            self.tracked_accounts = self.database.get_single_blockchain_addresses(
                cursor=cursor,
                blockchain=SupportedBlockchain.BITCOIN,
            )

    @staticmethod
    def get_balances(accounts: Sequence[BTCAddress]) -> dict[BTCAddress, FVal]:
        """Queries bitcoin balance APIs for the balances of accounts

        May raise:
        - RemoteError couldn't query any of the bitcoin balance APIs
        """
        return query_apis_via_callbacks(
            api_callbacks={
                'blockchain.info': _query_blockchain_info_balances,
                'blockstream.info': lambda accounts: _query_blockstream_or_mempool_balances(
                    accounts=accounts,
                    base_url=BLOCKSTREAM_BASE_URL,
                ),
                'mempool.space': lambda accounts: _query_blockstream_or_mempool_balances(
                    accounts=accounts,
                    base_url=MEMPOOL_SPACE_BASE_URL,
                ),
            },
            accounts=accounts,
        )

    @staticmethod
    def _query_tx_list_from_api(
            account: BTCAddress,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            existing_tx_id: str | None,
    ) -> list[BitcoinTx]:
        """Query raw bitcoin tx list from the block explorer apis and deserialize them.
        The txs are ordered with newest first from the api, with results automatically paginated.
        The next page is requested by specifying the last seen tx id from the previous result.

        If `existing_tx_id` is specified, querying will stop when that id is encountered, only
        returning new transactions since that id.

        Transactions newer than `to_timestamp` will be skipped, but `from_timestamp` is currently
        ignored - since the api returns newest to oldest, if we quit before querying to the end, the
        next query will stop at `existing_tx_id` and the skipped older txs would never be queried.

        Returns a list of deserialized BitcoinTxs.
        """
        # TODO: add support for querying the blockchain.info api for transactions as well.
        # https://www.blockchain.com/explorer/api/blockchain_api
        tx_list, tx_id, to_timestamp_ms = [], None, ts_sec_to_ms(to_timestamp)
        tx_endpoint = f'address/{account}/txs/chain'
        while True:
            for entry in (raw_tx_list := query_blockstream_or_mempool_api(
                    url_suffix=f'{tx_endpoint}/{tx_id}' if tx_id is not None else tx_endpoint,
                    # Specify the last seen tx id to request the next page  # noqa: E501
            )):
                tx = BitcoinTx.deserialize(entry)
                if tx.timestamp > to_timestamp_ms:
                    continue  # Haven't reached the requested range yet. Skip tx.
                if (tx_id := tx.tx_id) == existing_tx_id:
                    return tx_list  # All new txs have been queried. Skip tx and return.

                tx_list.append(tx)

            if len(raw_tx_list) < 25:
                break

        return tx_list

    def _query_account_transactions(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            account: BTCAddress,
    ) -> None:
        """Query transactions for the specified account and time range,
        decode them into HistoryEvents, and save the results to the db.
        """
        # TODO: websocket messages for progress updates when querying
        log.debug(f'Querying transactions for bitcoin account {account}')
        events_db = DBHistoryEvents(self.database)
        with self.database.conn.read_ctx() as cursor:
            last_tx_id = self.database.get_dynamic_cache(
                cursor=cursor,
                name=DBCacheDynamic.LAST_BITCOIN_TX_ID,
                address=account,
            )

        if len(tx_list := self._query_tx_list_from_api(
                account=account,
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                existing_tx_id=last_tx_id,
        )) == 0:
            log.debug(f'No new transactions found for bitcoin account {account}')
            return

        events = []
        for tx in tx_list:
            events.extend(self.decode_transaction(tx))

        with self.database.conn.write_ctx() as write_cursor:
            events_db.add_history_events(
                write_cursor=write_cursor,
                history=events,
            )
            self.database.set_dynamic_cache(
                write_cursor=write_cursor,
                name=DBCacheDynamic.LAST_BITCOIN_TX_ID,
                value=tx_list[0].tx_id,  # safe to use index zero since we checked tx_list length above  # noqa: E501
                address=account,
            )

    def query_transactions(
            self,
            from_timestamp: Timestamp,
            to_timestamp: Timestamp,
            addresses: list[BTCAddress],
    ):
        """Query, decode, and save bitcoin transactions in the specified time range
        for the specified addresses.
        """
        self.refresh_tracked_accounts()
        for address in addresses:
            self._query_account_transactions(
                from_timestamp=from_timestamp,
                to_timestamp=to_timestamp,
                account=address,
            )

    @staticmethod
    def create_event(
            tx: BitcoinTx,
            event_type: HistoryEventType,
            event_subtype: HistoryEventSubType,
            amount: FVal,
            notes: str | None = None,
            location_label: str | None = None,
    ):
        return HistoryEvent(
            event_identifier=f'btc_{tx.tx_id}',
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

    def decode_op_return(self, tx: BitcoinTx, raw_script: str) -> HistoryEvent | None:
        """Decode an OP_RETURN script into an informational history event.
        If data is valid utf-8 encoded text, show the decoded text in the event notes.
        Returns the history event or None on error.
        """
        parts = raw_script.split()
        if len(parts) == 3 and parts[0] == 'OP_RETURN' and parts[1].startswith('OP_PUSHBYTES_'):
            hex_data = parts[2]
        else:  # malformed op_return script
            return None

        try:  # maybe convert hex to ASCII
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

    def decode_transaction(self, tx: BitcoinTx) -> list[HistoryEvent]:
        """Decode a BitcoinTx into HistoryEvents

        If there are multiple inputs/outputs for the same address, events will only be created
        with the total in amount and total out amount for that address.

        If there are inputs from multiple addresses a fee event will be created for each address
        with the fee amounts proportional to the amounts spent by each address.

        Taproot TxIOs will currently all appear as TxIO for untracked wallets.

        Returns a list of HistoryEvents
        """
        events = []
        # Group input and output amounts by the total for each address.
        # (combines multiple UTXOs for the same address)
        per_address_in_out_totals = {
            True: defaultdict(lambda: ZERO),
            False: defaultdict(lambda: ZERO),
        }
        for tx_in_out_list, is_output in (
                (tx.inputs, False),
                (tx.outputs, True),
        ):
            per_address_totals = per_address_in_out_totals[is_output]
            for tx_io in tx_in_out_list:
                # Handle various types of scripts
                if tx_io.type == BtcScriptType.OP_RETURN:
                    if (event := self.decode_op_return(tx=tx, raw_script=tx_io.raw_script)) is not None:
                        events.append(event)
                    else:
                        log.error(f'Failed to decode OP_RETURN bitcoin script in {tx.tx_id} {tx_io}')
                    continue
                elif (
                    (address := tx_io.address) is None and
                    tx_io.type == BtcScriptType.P2PK
                ):  # derive the public key hash address from the raw public key used by p2pk
                    address = derive_p2pkh_from_p2pk(tx_io.pubkey)
                elif address is None:
                    log.error(f'Encountered {tx_io.type} script with no address in transaction {tx.tx_id}')
                    continue

                per_address_totals[address] += tx_io.value

        # Create fee events
        total_input = sum(per_address_in_out_totals[False].values())
        for address, amount in per_address_totals.items():
            per_address_totals[address] -= (fee_share := (amount / total_input) * tx.fee)
            if address not in self.tracked_accounts:
                continue  # only add the fee event for tracked accounts

            events.append(self.create_event(
                tx=tx,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                amount=fee_share,
                notes=f'Burn {fee_share} BTC for gas',
                location_label=address,
            ))

        input_totals = {k: v for k, v in per_address_in_out_totals[False].items() if v != ZERO}
        output_totals = {k: v for k, v in per_address_in_out_totals[True].items() if v != ZERO}
        in_len, out_len = len(input_totals), len(output_totals)
        if in_len == 0 or out_len == 0:
            # Inputs have all been spent on a fee or outputs have no value (likely op_return)
            if in_len != out_len:
                # only one is zero length - shouldn't happen since there would have to be
                # either more btc going in than came out, or vice versa
                log.error(
                    'Encountered Bitcoin transaction with mismatched '
                    'input/output amounts. Should not happen.',
                )

            return events  # no need to process further

        # TODO: Handle when an output goes back to an input address (self transfer / btc left over from the other outputs and fee)
        #  maybe just silently subtract this from the input amount? or informational event of some kind?

        if in_len == 1:
            sender = list(input_totals.keys())[0]
            sender_is_tracked = sender in self.tracked_accounts
            for receiver, amount in output_totals.items():
                if receiver in self.tracked_accounts:
                    if sender_is_tracked:
                        event_type = HistoryEventType.TRANSFER
                        verb = 'Transfer'
                        location_label = sender
                    else:
                        event_type = HistoryEventType.RECEIVE
                        verb = 'Receive'
                        location_label = receiver
                else:
                    if sender_is_tracked:
                        event_type = HistoryEventType.SPEND
                        verb = 'Send'
                        location_label = sender
                    else:
                        continue  # skip outputs to untracked addresses when sender isn't tracked

                events.append(self.create_event(
                    tx=tx,
                    event_type=event_type,
                    event_subtype=HistoryEventSubType.NONE,
                    amount=amount,
                    notes=f'{verb} {amount} BTC from {sender} to {receiver}',
                    location_label=location_label,
                ))
        else:  # Multi-input transaction. There isn't a direct A sent to B. Instead its all A's sent to all B's.
            for totals_dict, is_output in (
                (input_totals, False),
                (output_totals, True),
            ):
                other_side_addresses = ', '.join(totals_dict.keys())
                for address, amount in totals_dict.items():
                    if address not in self.tracked_accounts:
                        continue

                    if is_output:
                        event_type = HistoryEventType.RECEIVE
                        notes = f'Receive {amount} BTC from {other_side_addresses} to {address}'
                    else:
                        event_type = HistoryEventType.SPEND
                        notes = f'Send {amount} BTC from {address} to {other_side_addresses}'

                    events.append(self.create_event(
                        tx=tx,
                        event_type=event_type,
                        event_subtype=HistoryEventSubType.NONE,
                        amount=amount,
                        notes=notes,
                        location_label=address,
                    ))

        return events