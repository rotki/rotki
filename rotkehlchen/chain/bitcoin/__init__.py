from typing import Dict, List, Tuple

import requests

from rotkehlchen.errors import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.fval import FVal
from rotkehlchen.typing import BTCAddress
from rotkehlchen.utils.misc import satoshis_to_btc
from rotkehlchen.utils.network import request_get_dict


def _have_bc1_accounts(accounts: List[BTCAddress]) -> bool:
    return any(account.lower()[0:3] == 'bc1' for account in accounts)


def get_bitcoin_addresses_balances(accounts: List[BTCAddress]) -> Dict[BTCAddress, FVal]:
    """Queries blockchain.info or blockstream for the balances of accounts

    May raise:
    - RemotError if there is a problem querying blockchain.info or blockstream
    """
    source = 'blockchain.info'
    balances: Dict[BTCAddress, FVal] = {}
    try:
        if _have_bc1_accounts(accounts):
            # if 1 account is bech32 we have to query blockstream. blockchaininfo won't work
            source = 'blockstream'
            balances = {}
            for account in accounts:
                url = f'https://blockstream.info/api/address/{account}'
                response_data = request_get_dict(url=url, handle_429=True, backoff_in_seconds=4)
                stats = response_data['chain_stats']
                balance = int(stats['funded_txo_sum']) - int(stats['spent_txo_sum'])
                balances[account] = satoshis_to_btc(balance)
        else:
            # split the list of accounts into sublists of 80 addresses per list to overcome:
            # https://github.com/rotki/rotki/issues/3037
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
                    balances[entry['address']] = satoshis_to_btc(FVal(entry['final_balance']))
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

    return balances


def _check_blockstream_for_transactions(
        accounts: List[BTCAddress],
) -> Dict[BTCAddress, Tuple[bool, FVal]]:
    """May raise connection errors or KeyError"""
    have_transactions = {}
    for account in accounts:
        url = f'https://blockstream.info/api/address/{account}'
        response_data = request_get_dict(url=url, handle_429=True, backoff_in_seconds=4)
        stats = response_data['chain_stats']
        balance = satoshis_to_btc(int(stats['funded_txo_sum']) - int(stats['spent_txo_sum']))
        have_txs = stats['tx_count'] != 0
        have_transactions[account] = (have_txs, balance)

    return have_transactions


def _check_blockchaininfo_for_transactions(
        accounts: List[BTCAddress],
) -> Dict[BTCAddress, Tuple[bool, FVal]]:
    """May raise RemotError or KeyError"""
    have_transactions = {}
    params = '|'.join(accounts)
    btc_resp = request_get_dict(
        url=f'https://blockchain.info/multiaddr?active={params}',
        handle_429=True,
        # If we get a 429 then their docs suggest 10 seconds
        # https://blockchain.infoq/
        backoff_in_seconds=15,
    )
    for entry in btc_resp['addresses']:
        balance = satoshis_to_btc(entry['final_balance'])
        have_transactions[entry['address']] = (entry['n_tx'] != 0, balance)

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
            source = 'blockstream'
            have_transactions = _check_blockstream_for_transactions(accounts)
        else:
            source = 'blockchain.info'
            have_transactions = _check_blockchaininfo_for_transactions(accounts)
    except (
            requests.exceptions.RequestException,
            UnableToDecryptRemoteData,
            requests.exceptions.Timeout,
    ) as e:
        raise RemoteError(f'bitcoin external API request for transactions failed due to {str(e)}') from e  # noqa: E501
    except KeyError as e:
        raise RemoteError(
            f'Malformed response when querying bitcoin blockchain via {source}.'
            f'Did not find key {str(e)}',
        ) from e

    return have_transactions
