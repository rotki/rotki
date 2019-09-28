import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from rotkehlchen.errors import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.serialization.deserialize import deserialize_fval, deserialize_timestamp
from rotkehlchen.typing import EthAddress, EthereumTransaction, Timestamp
from rotkehlchen.user_messages import MessagesAggregator
from rotkehlchen.utils.misc import (
    convert_to_int,
    hexstring_to_bytes,
    request_get_dict,
    retry_calls,
)

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def read_hash(data: Dict[str, Any], key: str) -> bytes:
    try:
        result = hexstring_to_bytes(data[key])
    except ValueError:
        raise DeserializationError(
            f'Failed to read {key} as a hash during etherscan transaction query',
        )
    return result


def read_integer(data: Dict[str, Any], key: str) -> int:
    try:
        result = convert_to_int(data[key])
    except ValueError:
        raise DeserializationError(
            f'Failed to read {key} as an integer during etherscan transaction query',
        )
    return result


def deserialize_transaction_from_etherscan(
        data: Dict[str, Any],
        internal: bool,
) -> EthereumTransaction:
    """Reads dict data of a transaction from etherscan and deserializes it

    Can throw DeserializationError if something is wrong
    """
    try:
        # internal tx list contains no gasprice
        gas_price = FVal(-1) if internal else FVal(data['gasPrice'])
        tx_hash = read_hash(data, 'hash')
        input_data = read_hash(data, 'input')
        timestamp = deserialize_timestamp(data['timeStamp'])

        block_number = read_integer(data, 'blockNumber')
        nonce = -1 if internal else read_integer(data, 'nonce')

        return EthereumTransaction(
            timestamp=timestamp,
            block_number=block_number,
            tx_hash=tx_hash,
            from_address=data['from'],
            to_address=data['to'],
            value=deserialize_fval(data['value']),
            gas=deserialize_fval(data['gas']),
            gas_price=gas_price,
            gas_used=deserialize_fval(data['gasUsed']),
            input_data=input_data,
            nonce=nonce,
        )
    except KeyError as e:
        raise DeserializationError(f'Etherscan ethereum transaction missing expected key {str(e)}')


def query_ethereum_txlist(
        address: EthAddress,
        msg_aggregator: MessagesAggregator,
        internal: bool,
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
) -> List[EthereumTransaction]:
    """Query ethereum tx list"""
    log.debug(
        'Querying etherscan for tx list',
        sensitive_log=True,
        internal=internal,
        eth_address=address,
        from_block=from_block,
        to_block=to_block,
    )

    result = list()
    if internal:
        reqstring = (
            'https://api.etherscan.io/api?module=account&action='
            'txlistinternal&address={}'.format(address)
        )
    else:
        reqstring = (
            'https://api.etherscan.io/api?module=account&action='
            'txlist&address={}'.format(address)
        )
    if from_block:
        reqstring += '&startblock={}'.format(from_block)
    if to_block:
        reqstring += '&endblock={}'.format(to_block)

    resp = request_get_dict(reqstring)

    if 'status' not in resp or convert_to_int(resp['status']) != 1:
        status = convert_to_int(resp['status'])
        if status == 0 and resp['message'] == 'No transactions found':
            return list()

        log.error(
            'Querying etherscan for tx list failed',
            sensitive_log=True,
            internal=internal,
            eth_address=address,
            from_block=from_block,
            to_block=to_block,
            error=resp['message'],
        )
        # else unknown error
        raise ValueError(
            'Failed to query txlist from etherscan with query: {} . '
            'Response was: {}'.format(reqstring, resp),
        )

    log.debug('Etherscan tx list query result', results_num=len(resp['result']))
    for v in resp['result']:
        try:
            tx = deserialize_transaction_from_etherscan(data=v, internal=internal)
        except DeserializationError as e:
            msg_aggregator.add_warning(f'{str(e)}. Skipping transaction')
            continue

        result.append(tx)

    return result


def query_etherscan_for_transactions(
        db: 'DBHandler',
        msg_aggregator: MessagesAggregator,
        from_ts: Optional[Timestamp] = None,
        to_ts: Optional[Timestamp] = None,
) -> List[EthereumTransaction]:
    transactions: List[EthereumTransaction] = list()

    accounts = db.get_blockchain_accounts()
    for address in accounts.eth:
        # If we already have any transactions in the DB for this from_address
        # from to_ts and on then that means the range has already been queried
        if to_ts:
            existing_txs = db.get_ethereum_transactions(from_ts=to_ts, address=address)
            if len(existing_txs) > 0:
                # So just query the DB only here
                transactions.extend(
                    db.get_ethereum_transactions(from_ts=from_ts, to_ts=to_ts, address=address),
                )
                continue

        # else we have to query etherscan for this address
        new_transactions = retry_calls(
            times=5,
            location='etherscan',
            handle_429=False,
            backoff_in_seconds=0,
            method_name='query_ethereum_txlist',
            function=query_ethereum_txlist,
            # function's arguments
            address=address,
            msg_aggregator=msg_aggregator,
            internal=False,
        )
        new_transactions.extend(
            retry_calls(
                times=5,
                location='etherscan',
                handle_429=False,
                backoff_in_seconds=0,
                method_name='query_ethereum_txlist_internal',
                function=query_ethereum_txlist,
                # function's arguments
                address=address,
                msg_aggregator=msg_aggregator,
                internal=True,
            ),
        )

        # and finally also save the transactions in the DB
        db.add_ethereum_transactions(ethereum_transactions=new_transactions, from_etherscan=True)
        transactions.extend(new_transactions)

    transactions.sort(key=lambda tx: tx.timestamp)
    return transactions
