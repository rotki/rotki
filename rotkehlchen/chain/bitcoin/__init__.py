from typing import Dict, List, Tuple

import requests

from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import ensure_type
from rotkehlchen.types import BTCAddress
from rotkehlchen.utils.misc import satoshis_to_btc
from rotkehlchen.utils.network import request_get_dict


def _have_bc1_accounts(accounts: List[BTCAddress]) -> bool:
    return any(account.lower()[0:3] == 'bc1' for account in accounts)


def _query_blockstream_or_mempool(
        accounts: List[BTCAddress],
        base_url: str,
) -> Dict[BTCAddress, FVal]:
    """Queries balances from blockstream.info
    May raise:
    - RemoteError if got problems with querying the API
    - KeyError if got unexpected json structure
    - DeserializationError if got unexpected json values
    """
    balances = {}
    for account in accounts:
        url = base_url + account
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


def _query_blockstream_info(accounts: List[BTCAddress]) -> Dict[BTCAddress, FVal]:
    return _query_blockstream_or_mempool(
        accounts=accounts,
        base_url='https://blockstream.info/api/address/',
    )


def _query_mempool_space(accounts: List[BTCAddress]) -> Dict[BTCAddress, FVal]:
    return _query_blockstream_or_mempool(
        accounts=accounts,
        base_url='https://mempool.space/api/address/',
    )


def _query_blockchain_info(accounts: List[BTCAddress]) -> Dict[BTCAddress, FVal]:
    """Queries balances from blockchain.info
    May raise:
    - RemoteError if got problems with querying the API
    - KeyError if got unexpected json structure
    - DeserializationError if got unexpected json values
    """
    balances: Dict[BTCAddress, FVal] = {}
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


def get_bitcoin_addresses_balances(
        accounts: List[BTCAddress],
) -> Dict[BTCAddress, FVal]:
    """Queries bitcoin balance APIs for the balances of accounts

    May raise:
    - RemoteError couldn't query any of the bitcoin balance APIs
    """
    if _have_bc1_accounts(accounts) is True:
        api_callbacks = {
            'blockstream.info': _query_blockstream_info,
            'mempool.space': _query_mempool_space,
        }
    else:
        api_callbacks = {
            'blockchain.info': _query_blockchain_info,
            'blockstream.info': _query_blockstream_info,
            'mempool.space': _query_mempool_space,
        }
    errors: Dict[str, str] = {}
    for api_name, callback in api_callbacks.items():
        try:
            balances = callback(accounts)
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
            errors[api_name] = f'Got unexpected response from {api_name}. Couldn\'t find key {str(e)}'  # noqa: E501
        else:
            return balances

    serialized_errors = ', '.join(f'{source} error is: "{error}"' for (source, error) in errors.items())  # noqa: E501
    raise RemoteError(f'Bitcoin external API request for balances failed. {serialized_errors}')  # noqa: E501


def _check_blockstream_for_transactions(
        accounts: List[BTCAddress],
) -> Dict[BTCAddress, Tuple[bool, FVal]]:
    """May raise:
    - RemoteError if couldn't query
    - KeyError if response structure differs from the expected one
    - DeserializationError if response values differ from the expected
    """
    have_transactions = {}
    for account in accounts:
        url = f'https://blockstream.info/api/address/{account}'
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
        have_txs = stats['tx_count'] != 0
        have_transactions[account] = (have_txs, balance)

    return have_transactions


def _check_blockchaininfo_for_transactions(
        accounts: List[BTCAddress],
) -> Dict[BTCAddress, Tuple[bool, FVal]]:
    """May raise RemoteError or KeyError"""
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
    except DeserializationError as e:
        raise RemoteError(f'Couldn\'t read data from the response due to {str(e)}') from e

    return have_transactions
