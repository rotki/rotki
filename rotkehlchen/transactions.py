import logging
from typing import TYPE_CHECKING, List, Optional

from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import EthAddress, EthereumTransaction, Timestamp
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


def query_ethereum_txlist(
        address: EthAddress,
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
        # internal tx list contains no gasprice
        gas_price = FVal(-1) if internal else FVal(v['gasPrice'])
        result.append(EthereumTransaction(
            timestamp=Timestamp(convert_to_int(v['timeStamp'])),
            block_number=convert_to_int(v['blockNumber']),
            tx_hash=hexstring_to_bytes(v['hash']),
            from_address=v['from'],
            to_address=v['to'],
            value=FVal(v['value']),
            gas=FVal(v['gas']),
            gas_price=gas_price,
            gas_used=FVal(v['gasUsed']),
            input_data=hexstring_to_bytes(v['input']),
            nonce=convert_to_int(v['nonce']),
        ))

    return result


def query_etherscan_for_transactions(
        accounts: List[EthAddress],
        db: 'DBHandler',
        from_ts: Optional[Timestamp] = None,
        to_ts: Optional[Timestamp] = None,
) -> List[EthereumTransaction]:
    transactions: List[EthereumTransaction] = list()
    for address in accounts:
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
                internal=True,
            ),
        )

        # and finally also save the transactions in the DB
        db.add_ethereum_transactions(ethereum_transactions=new_transactions)
        transactions.extend(new_transactions)

    transactions.sort(key=lambda tx: tx.timestamp)
    return transactions
