from typing import Dict, List

from rotkehlchen.typing import (
    EthereumTransaction,
    EthAddress,
    Timestamp,
)
from rotkehlchen.utils import retry_calls, convert_to_int, request_get
from rotkehlchen.fval import FVal


def query_ethereum_txlist(
        address: EthAddress,
        internal: bool,
        from_block: int = None,
        to_block: int = None,
) -> List[EthereumTransaction]:
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

    resp = request_get(reqstring)

    if 'status' not in resp or convert_to_int(resp['status']) != 1:
        status = convert_to_int(resp['status'])
        if status == 0 and resp['message'] == 'No transactions found':
            return list()

        # else unknown error
        raise ValueError(
            'Failed to query txlist from etherscan with query: {} . '
            'Response was: {}'.format(reqstring, resp)
        )

    for v in resp['result']:
        # internal tx list contains no gasprice
        gas_price = FVal(-1) if internal else FVal(v['gasPrice'])
        result.append(EthereumTransaction(
            timestamp=convert_to_int(v['timeStamp']),
            block_number=convert_to_int(v['blockNumber']),
            hash=v['hash'],
            from_address=v['from'],
            to_address=v['to'],
            value=FVal(v['value']),
            gas=FVal(v['gas']),
            gas_price=gas_price,
            gas_used=FVal(v['gasUsed']),
        ))

    return result


def query_etherscan_for_transactions(accounts: List[EthAddress]) -> List[EthereumTransaction]:
    transactions: List[EthereumTransaction] = list()
    for account in accounts:
        transactions.extend(
            retry_calls(
                5,
                'etherscan',
                'query_ethereum_txlist',
                query_ethereum_txlist,
                account,
                False,
            )
        )
        transactions.extend(
            retry_calls(
                5,
                'etherscan',
                'query_ethereum_txlist_internal',
                query_ethereum_txlist,
                account,
                True,
            )
        )

    transactions.sort(key=lambda tx: tx.timestamp)
    return transactions


def transactions_from_dictlist(
        given_transactions: Dict,
        start_ts: Timestamp,
        end_ts: Timestamp,
) -> List[EthereumTransaction]:
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
            timestamp=convert_to_int(given_tx['timestamp']),
            block_number=convert_to_int(given_tx['block_number']),
            hash=given_tx['hash'],
            from_address=given_tx['from_address'],
            to_address=given_tx['to_address'],
            value=FVal(given_tx['value']),
            gas=FVal(given_tx['gas']),
            gas_price=FVal(given_tx['gas_price']),
            gas_used=FVal(given_tx['gas_used']),
        ))

    return returned_transactions
