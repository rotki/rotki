import json
import urllib2
from collections import namedtuple
from utils import retry_calls
from decimal import Decimal

EthereumTransaction = namedtuple(
    'EthereumTransaction',
    (
        'timestamp',
        'block_number',
        'hash',
        'from_address',
        'to_address',
        'value',
        'gas',
        'gas_price',
        'gas_used',
    )
)


def query_txlist(address, internal, from_block=None, to_block=None):
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

    resp = urllib2.urlopen(urllib2.Request(reqstring))
    resp = json.loads(resp.read())

    if 'status' not in resp or int(resp['status']) != 1:
        status = int(resp['status'])
        if status == 0 and resp['message'] == 'No transactions found':
            return list()

        # else unknown error
        raise ValueError(
            'Failed to query txlist from etherscan with query: {} . '
            'Response was: {}'.format(reqstring, resp)
        )

    for v in resp['result']:
        # internal tx list contains no gasprice
        gas_price = -1 if internal else Decimal(v['gasPrice'])
        result.append(EthereumTransaction(
            timestamp=Decimal(v['timeStamp']),
            block_number=Decimal(v['blockNumber']),
            hash=v['hash'],
            from_address=v['from'],
            to_address=v['to'],
            value=Decimal(v['value']),
            gas=Decimal(v['gas']),
            gas_price=gas_price,
            gas_used=Decimal(v['gasUsed']),
        ))

    return result


def query_etherscan_for_transactions(accounts):
    transactions = list()
    for account in accounts:
        transactions.extend(
            retry_calls(5, 'etherscan', 'query_txlist', query_txlist, account, False)
        )
        transactions.extend(
            retry_calls(5, 'etherscan', 'query_txlist_internal', query_txlist, account, True)
        )

    transactions.sort(key=lambda tx: tx.timestamp)
    return transactions


def transactions_from_dictlist(given_transactions, start_ts, end_ts):
    """ Gets a list of transaction, most probably read from the json files and
    a time period. Returns it as a list of the transaction tuples that are inside the time period
    """
    returned_transactions = list()
    for given_tx in given_transactions:
        if given_tx['timestamp'] < start_ts:
            continue
        if given_tx['timestamp'] > end_ts:
            break

        returned_transactions.append(EthereumTransaction(
            timestamp=given_tx['timestamp'],
            block_number=Decimal(given_tx['block_number']),
            hash=given_tx['hash'],
            from_address=given_tx['from_address'],
            to_address=given_tx['to_address'],
            value=Decimal(given_tx['value']),
            gas=Decimal(given_tx['gas']),
            gas_price=Decimal(given_tx['gas_price']),
            gas_used=Decimal(given_tx['gas_used']),
        ))

    return returned_transactions
