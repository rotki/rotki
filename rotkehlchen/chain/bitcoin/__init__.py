from typing import Dict, List, Tuple

import requests

from rotkehlchen.errors import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.fval import FVal
from rotkehlchen.typing import BTCAddress
from rotkehlchen.utils.misc import request_get, request_get_dict, satoshis_to_btc


def _prepare_blockcypher_accounts(accounts: List[BTCAddress]) -> List[BTCAddress]:
    """bech32 accounts have to be given lowercase to the blockcypher query.

    No idea why.
    """
    new_accounts: List[BTCAddress] = []
    for x in accounts:
        lowered = x.lower()
        if lowered[0:3] == 'bc1':
            new_accounts.append(BTCAddress(lowered))
        else:
            new_accounts.append(x)

    return new_accounts


def _have_bc1_accounts(accounts: List[BTCAddress]) -> bool:
    return any(account.lower()[0:3] == 'bc1' for account in accounts)


def get_bitcoin_addresses_balances(accounts: List[BTCAddress]) -> Dict[BTCAddress, FVal]:
    """Queries blockchain.info or blockcypher for the balances of accounts

    May raise:
    - RemotError if there is a problem querying blockchain.info or blockcypher
    """
    source = 'blockchain.info'
    balances = {}
    try:
        if _have_bc1_accounts(accounts):
            # if 1 account is bech32 we have to query blockcypher. blockchaininfo won't work
            source = 'blockcypher.com'
            new_accounts = _prepare_blockcypher_accounts(accounts)

            # blockcypher's batching takes up as many api queries as the batch,
            # and the api rate limit is 3 requests per second. So we should make
            # sure each batch is of max size 3
            # https://www.blockcypher.com/dev/bitcoin/#batching
            batches = [new_accounts[x: x + 3] for x in range(0, len(new_accounts), 3)]
            total_idx = 0
            for batch in batches:
                params = ';'.join(batch)
                url = f'https://api.blockcypher.com/v1/btc/main/addrs/{params}/balance'
                response_data = request_get(url=url, handle_429=True, backoff_in_seconds=4)

                if isinstance(response_data, dict):
                    # If only one account was requested put it in a list so the
                    # rest of the code works
                    response_data = [response_data]

                for idx, entry in enumerate(response_data):
                    # we don't use the returned address as it may be lowercased
                    balances[accounts[total_idx + idx]] = satoshis_to_btc(
                        FVal(entry['final_balance']),
                    )
                total_idx += len(batch)
        else:
            params = '|'.join(accounts)
            btc_resp = request_get_dict(
                url=f'https://blockchain.info/multiaddr?active={params}',
                handle_429=True,
                # If we get a 429 then their docs suggest 10 seconds
                # https://blockchain.info/q
                backoff_in_seconds=10,
            )
            for idx, entry in enumerate(btc_resp['addresses']):
                balances[accounts[idx]] = satoshis_to_btc(FVal(entry['final_balance']))
    except (
            requests.exceptions.ConnectionError,
            UnableToDecryptRemoteData,
            requests.exceptions.Timeout,
    ) as e:
        raise RemoteError(f'bitcoin external API request for balances failed due to {str(e)}')
    except KeyError as e:
        raise RemoteError(
            f'Malformed response when querying bitcoin blockchain via {source}.'
            f'Did not find key {e}',
        )

    return balances


def _check_blockcypher_for_transactions(
        accounts: List[BTCAddress],
) -> Dict[BTCAddress, Tuple[bool, FVal]]:
    have_transactions = {}
    new_accounts = _prepare_blockcypher_accounts(accounts)
    # blockcypher's batching takes up as many api queries as the batch,
    # and the api rate limit is 3 requests per second. So we should make
    # sure each batch is of max size 3
    # https://www.blockcypher.com/dev/bitcoin/#batching
    batches = [new_accounts[x: x + 3] for x in range(0, len(new_accounts), 3)]
    total_idx = 0
    for batch in batches:
        params = ';'.join(batch)
        url = f'https://api.blockcypher.com/v1/btc/main/addrs/{params}/balance'
        response_data = request_get(url=url, handle_429=True, backoff_in_seconds=4)

        if isinstance(response_data, dict):
            # If only one account was requested put it in a list so the
            # rest of the code works
            response_data = [response_data]

        for idx, entry in enumerate(response_data):
            balance = satoshis_to_btc(FVal(entry['final_balance']))
            # we don't use the returned address as it may be lowercased
            have_transactions[accounts[total_idx + idx]] = (entry['final_n_tx'] != 0, balance)
        total_idx += len(batch)

    return have_transactions


def _check_blockchaininfo_for_transactions(
        accounts: List[BTCAddress],
) -> Dict[BTCAddress, Tuple[bool, FVal]]:
    have_transactions = {}
    params = '|'.join(accounts)
    btc_resp = request_get_dict(
        url=f'https://blockchain.info/multiaddr?active={params}',
        handle_429=True,
        # If we get a 429 then their docs suggest 10 seconds
        # https://blockchain.infoq/
        backoff_in_seconds=15,
    )
    for idx, entry in enumerate(btc_resp['addresses']):
        balance = satoshis_to_btc(entry['final_balance'])
        have_transactions[accounts[idx]] = (entry['n_tx'] != 0, balance)

    return have_transactions


def have_bitcoin_transactions(accounts: List[BTCAddress]) -> Dict[BTCAddress, Tuple[bool, FVal]]:
    """
    Takes a list of addresses and returns a mapping of which addresses have had transactions
    and also their current balance

    May raise:
    - RemoteError if any of the queried websites fail to be queried
    """
    try:
        if _have_bc1_accounts(accounts):
            have_transactions = _check_blockcypher_for_transactions(accounts)
        else:
            have_transactions = _check_blockchaininfo_for_transactions(accounts)
    except (
            requests.exceptions.ConnectionError,
            UnableToDecryptRemoteData,
            requests.exceptions.Timeout,
    ) as e:
        raise RemoteError(f'bitcoin external API request for transactions failed due to {str(e)}')

    return have_transactions
