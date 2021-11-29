from collections import defaultdict
from copy import deepcopy
import logging
from typing import (
    Any,
    Dict,
    DefaultDict,
    List,
    NamedTuple,
    Tuple,
    TYPE_CHECKING,
    Optional,
)

import requests

from rotkehlchen.db.filtering import BTCTransactionsFilterQuery
from rotkehlchen.errors import DeserializationError, RemoteError, UnableToDecryptRemoteData
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_timestamp
from rotkehlchen.typing import BTCAddress
from rotkehlchen.utils.misc import ts_now
from rotkehlchen.utils.mixins.lockable import LockableQueryMixIn
from rotkehlchen.utils.mixins.dbenum import DBEnumMixIn
from rotkehlchen.utils.mixins.serializableenum import SerializableEnumMixin
from rotkehlchen.utils.network import request_get, request_get_dict
from rotkehlchen.typing import Timestamp


if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)
FREE_BTC_TX_LIMIT = 250
BTCTransactionDBTuple = Tuple[
    str,  # hash
    int,  # timestamp
    int,  # block number
    str,  # inputs
    str,  # outputs
    int,  # amount in satoshi
    str,  # address
    str,  # action type
]


class BtcTransactionType(DBEnumMixIn, SerializableEnumMixin):
    INCOME = 1
    EXPENSE = 2


class BtcTransaction(NamedTuple):
    tx_hash: str
    timestamp: Timestamp
    block_number: int
    amount: int
    action_type: BtcTransactionType
    inputs: List[str]
    outputs: List[str]
    address: str

    def serialize(self) -> Dict[str, Any]:
        result = self._asdict()
        result['amount'] = str(result['amount'])
        return result

    @classmethod
    def deserialize_from_db(cls, entry: BTCTransactionDBTuple) -> 'BtcTransaction':
        inputs = entry[3].split(',')
        outputs = entry[4].split(',')
        action_type = BtcTransactionType.deserialize_from_db(entry[7])
        return BtcTransaction(
            tx_hash=entry[0],
            timestamp=deserialize_timestamp(entry[1]),
            block_number=entry[2],
            action_type=action_type,
            amount=entry[5],
            inputs=inputs,
            outputs=outputs,
            address=entry[6],
        )

    def serialize_for_db(self) -> BTCTransactionDBTuple:
        return (
            self.tx_hash,
            int(self.timestamp),
            self.block_number,
            ",".join(self.inputs),
            ",".join(self.outputs),
            self.amount,
            str(self.address),
            self.action_type.serialize_for_db(),
        )


class BtcTransactions(LockableQueryMixIn):

    def __init__(self, database: 'DBHandler') -> None:
        super().__init__()
        self.database = database
        self.queryrange_formatstr = 'btctxs_{address}'

    def single_address_query_transactions(
        self,
        address: BTCAddress,
        start_ts: Timestamp,
        end_ts: Timestamp,
    ) -> None:
        self.database.get_used_query_range(
            name=self.queryrange_formatstr.format(address=address),
        )
        new_transactions = []
        try:
            if address.startswith('bc1'):
                # if the account is bech32 we have to query blockstream. blockchaininfo won't work
                source = 'blockstream'
                url = f'https://blockstream.info/api/address/{address}/txs'
                response = request_get(url=url, handle_429=True, backoff_in_seconds=4)
                if isinstance(response, list):
                    for tx in response:
                        action_type = BtcTransactionType.EXPENSE
                        amount = None
                        inputs, outputs = [], []
                        for input_data in tx['vin']:
                            if input_data['scriptpubkey_address'] == address:
                                action_type = BtcTransactionType.INCOME
                                amount = input_data['value']
                            inputs.append(input_data['scriptpubkey_address'])
                        for output_data in tx['vout']:
                            if output_data['scriptpubkey_address'] == address:
                                amount = output_data['value']
                            outputs.append(input_data['scriptpubkey_address'])
                        if amount is None:
                            log.error(
                                f'Failed to find address in BTC transaction {tx["txid"]}',
                            )
                            continue
                        new_transactions.append(BtcTransaction(
                            tx_hash=tx['txid'],
                            timestamp=Timestamp(tx['status']['block_time']),
                            block_number=tx['status']['block_height'],
                            action_type=action_type,
                            amount=amount,
                            inputs=inputs,
                            outputs=outputs,
                            address=address,
                        ))
            else:
                response = request_get_dict(
                    url=f'https://blockchain.info/rawaddr/{address}',
                    handle_429=True,
                    # If we get a 429 then their docs suggest 10 seconds
                    # https://blockchain.info/q
                    backoff_in_seconds=10,
                )
                for tx in response['txs']:
                    amount = tx['result']
                    action_type = BtcTransactionType.INCOME
                    if amount < 0:
                        amount = abs(amount)
                        action_type = BtcTransactionType.EXPENSE
                    new_transactions.append(BtcTransaction(
                        tx_hash=tx['hash'],
                        timestamp=Timestamp(tx['time']),
                        block_number=tx['block_index'],
                        action_type=action_type,
                        amount=amount,
                        inputs=inputs,
                        outputs=outputs,
                        address=address,
                    ))
        except (
                requests.exceptions.RequestException,
                UnableToDecryptRemoteData,
                requests.exceptions.Timeout,
        ) as e:
            raise RemoteError(f'bitcoin external API request for balances failed due to {str(e)}') from e  # noqa: E501
        except KeyError as e:
            raise RemoteError(
                f'Malformed response when querying bitcoin blockchain via {source}.'
                f'Did not find key {e}',
            ) from e

        if len(new_transactions) != 0:
            self.store_btc_transactions(new_transactions)

        # and also set the last queried timestamps for the address
        self.database.update_used_query_range(
            name=self.queryrange_formatstr.format(address=address),
            start_ts=start_ts,
            end_ts=end_ts,
        )

    def store_btc_transactions(
        self,
        bitcoin_transactions: List[BtcTransaction],
    ) -> None:
        """Stores last retrieved transactions in the database"""
        tx_tuples: List[BTCTransactionDBTuple] = []
        for tx in bitcoin_transactions:
            tx_tuples.append(tx.serialize_for_db())
        query = """
            INSERT INTO bitcoin_transactions (
                tx_hash,
                timestamp,
                block_number,
                inputs,
                outputs,
                amount,
                address,
                action_type,
            )
            VALUES (?, ?. ?, ?, ?, ?, ?, ?)
        """
        self.database.write_tuples(
            tuple_type='bitcoin_transaction',
            query=query,
            tuples=tx_tuples,
        )

    def get_btc_transactions(
        self,
        filter_: BTCTransactionsFilterQuery,
    ) -> Tuple[List[BtcTransaction], int]:
        """Returns a tuple with 2 entries.
        First entry is a list of btc transactions optionally filtered by
        time and/or from address and pagination.
        Second is the number of entries found for the current filter ignoring pagination.
        """
        cursor = self.database.conn.cursor()
        query, bindings = filter_.prepare()
        query = 'SELECT * FROM bitcoin_transactions ' + query
        results = cursor.execute(query, bindings)

        bitcoin_transactions = []
        for transaction_raw in results:
            try:
                tx = BtcTransaction.deserialize_from_db(transaction_raw)
            except DeserializationError as e:
                self.database.msg_aggregator.add_error(
                    f'Error deserializing bitcoin transaction from the DB. '
                    f'Skipping it. Error was: {str(e)}',
                )
                continue
            bitcoin_transactions.append(tx)

        if filter_.pagination is not None:
            no_pagination_filter = deepcopy(filter_)
            no_pagination_filter.pagination = None
            query, bindings = no_pagination_filter.prepare()
            query = 'SELECT COUNT(*) FROM bitcoin_transactions ' + query
            results = cursor.execute(query, bindings).fetchone()
            total_filter_count = results[0]
        else:
            total_filter_count = len(bitcoin_transactions)

        return bitcoin_transactions, total_filter_count

    def _return_transactions_maybe_limit(
            self,
            requested_addresses: Optional[List[BTCAddress]],
            transactions: List[BtcTransaction],
            with_limit: bool,
    ) -> List[BtcTransaction]:
        if with_limit is False:
            return transactions

        count_map: DefaultDict[BTCAddress, int] = defaultdict(int)
        for tx in transactions:
            count_map[BTCAddress(tx.address)] += 1

        # for address, count in count_map.items():
        #    self.ethereum.tx_per_address[address] = count

        # if requested_addresses is not None:
        #    transactions_for_other_addies = sum(x for addy, x in self.ethereum.tx_per_address.items() if addy not in requested_addresses)  # noqa: E501
        #    remaining_num_tx = FREE_ETH_TX_LIMIT - transactions_for_other_addies
        #    returning_tx_length = min(remaining_num_tx, len(transactions))
        # else:
        #    returning_tx_length = min(FREE_ETH_TX_LIMIT, len(transactions))
        returning_tx_length = len(transactions)
        return transactions[:returning_tx_length]

    def query(
        self,
        filter_query: BTCTransactionsFilterQuery,
        with_limit: bool = False,
        only_cache: bool = False,
    ) -> Tuple[List[BtcTransaction], int]:
        """May raise:
            - RemoteError if there is a problem retrieving information from blockchain.info
            or blockstream
            - pysqlcipher3.dbapi2.OperationalError if the SQL query fails due to
            invalid filtering arguments.
        """
        query_addresses = filter_query.addresses

        if query_addresses is not None:
            accounts = query_addresses
        else:
            accounts = self.database.get_blockchain_accounts().btc

        if only_cache is False:
            f_from_ts = filter_query.from_ts
            f_to_ts = filter_query.to_ts
            from_ts = Timestamp(0) if f_from_ts is None else f_from_ts
            to_ts = ts_now() if f_to_ts is None else f_to_ts
            for address in accounts:
                self.single_address_query_transactions(
                    address=address,
                    start_ts=from_ts,
                    end_ts=to_ts,
                )

        transactions, total_filter_count = self.get_btc_transactions(filter_=filter_query)
        return (
            self._return_transactions_maybe_limit(
                requested_addresses=query_addresses,
                transactions=transactions,
                with_limit=with_limit,
            ),
            total_filter_count,
        )
