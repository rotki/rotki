import logging
from typing import Dict, List

from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import EthAddress, EthereumTransaction, Timestamp
from rotkehlchen.utils import convert_to_int, request_get, retry_calls

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def query_ethereum_txlist(
        address: EthAddress,
        internal: bool,
        from_block: int = None,
        to_block: int = None,
) -> List[EthereumTransaction]:
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

    resp = request_get(reqstring)

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
        # internal tx list contains no gasprice
        gas_price = FVal(-1) if internal else FVal(v['gasPrice'])
        result.append(EthereumTransaction(
            timestamp=Timestamp(convert_to_int(v['timeStamp'])),
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
            ),
        )
        transactions.extend(
            retry_calls(
                5,
                'etherscan',
                'query_ethereum_txlist_internal',
                query_ethereum_txlist,
                account,
                True,
            ),
        )

    transactions.sort(key=lambda tx: tx.timestamp)
    return transactions


def transactions_from_dictlist(
        given_transactions: List[Dict],
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

        timestamp = Timestamp(convert_to_int(given_tx['timestamp']))
        tx_hash = given_tx['hash']
        from_address = given_tx['from_address']
        to_address = given_tx['to_address']
        value = FVal(given_tx['value'])
        gas = FVal(given_tx['gas'])
        gas_price = FVal(given_tx['gas_price'])
        gas_used = FVal(given_tx['gas_used'])
        log.debug(
            'Processing eth transaction',
            sensitive_log=True,
            timestamp=timestamp,
            eth_tx_hash=tx_hash,
            from_eth_address=from_address,
            to_eth_address=to_address,
            tx_value=value,
            gas=gas,
            gas_price=gas_price,
            gas_used=gas_used,
        )

        returned_transactions.append(EthereumTransaction(
            timestamp=timestamp,
            block_number=convert_to_int(given_tx['block_number']),
            hash=tx_hash,
            from_address=from_address,
            to_address=to_address,
            value=value,
            gas=gas,
            gas_price=gas_price,
            gas_used=gas_used,
        ))

    return returned_transactions
