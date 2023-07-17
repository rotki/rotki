from collections.abc import Sequence

import requests

from rotkehlchen.chain.bitcoin.bch.utils import cash_to_legacy_address
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_fval
from rotkehlchen.types import BTCAddress
from rotkehlchen.utils.misc import satoshis_to_btc
from rotkehlchen.utils.network import request_get, request_get_dict

HASKOIN_BASE_URL = 'https://api.haskoin.com'


def get_bitcoin_cash_addresses_balances(accounts: Sequence[BTCAddress]) -> dict[BTCAddress, FVal]:
    """Queries api.haskoin.com for the balances of BCH accounts.

    May raise:
    - RemoteError if there is a problem querying api.haskoin.com
    """
    balances: dict[BTCAddress, FVal] = {}
    try:
        accounts_chunks = [accounts[x:x + 80] for x in range(0, len(accounts), 80)]
        for accounts_chunk in accounts_chunks:
            params = ','.join(accounts_chunk)
            bch_resp = request_get(url=f'{HASKOIN_BASE_URL}/bch/address/balances?addresses={params}')  # noqa: E501
            for entry in bch_resp:
                # Try and get the initial address passed to the request.
                # This is because the API only returns CashAddr format as response.
                if entry['address'] in accounts_chunk:
                    balances[entry['address']] = satoshis_to_btc(deserialize_fval(
                        value=entry['confirmed'],
                        name='balance',
                        location='bitcoin cash balance querying',
                    ))
                # if the address was initially provided in CashAddr format without the prefix
                elif entry['address'].split(':')[1] in accounts_chunk:
                    balances[entry['address'].split(':')[1]] = satoshis_to_btc(deserialize_fval(
                        value=entry['confirmed'],
                        name='balance',
                        location='bitcoin cash balance querying',
                    ))
                else:
                    address = cash_to_legacy_address(entry['address'])
                    if address is not None:
                        balances[address] = satoshis_to_btc(deserialize_fval(
                            value=entry['confirmed'],
                            name='balance',
                            location='bitcoin cash balance querying',
                        ))
    except requests.exceptions.RequestException as e:
        raise RemoteError(f'Bitcoin Cash external API request for balances failed due to {e!s}') from e  # noqa: E501
    except KeyError as e:
        raise RemoteError(
            f'Malformed response when querying Bitcoin Cash blockchain via {HASKOIN_BASE_URL}. '
            f'Did not find key {e}',
        ) from e
    except DeserializationError as e:
        raise RemoteError(
            f'Malformed response when querying Bitcoin Cash blockchain via {HASKOIN_BASE_URL}. '
            'Unable to parse balance.',
        ) from e

    return balances


def _check_haskoin_for_transactions(
        accounts: Sequence[BTCAddress],
) -> dict[BTCAddress, tuple[bool, FVal]]:
    """Checks if the BCH addresses have at least a transaction.
    May raise RemoteError or KeyError or DeserializationError"""
    have_transactions = {}
    params = '|'.join(accounts)
    bch_resp = request_get_dict(url=f'{HASKOIN_BASE_URL}/bch/blockchain/multiaddr?active={params}')
    for entry in bch_resp['addresses']:
        if entry['address'] in accounts:
            balance = satoshis_to_btc(deserialize_fval(
                value=entry['final_balance'],
                name='balance',
                location='bitcoin cash balance querying',
            ))
            have_transactions[entry['address']] = (entry['n_tx'] != 0, balance)
        else:
            address = cash_to_legacy_address(entry['address'])
            balance = satoshis_to_btc(deserialize_fval(
                value=entry['final_balance'],
                name='balance',
                location='bitcoin cash balance querying',
            ))
            if address is not None:
                have_transactions[address] = (entry['n_tx'] != 0, balance)
    return have_transactions


def have_bch_transactions(accounts: Sequence[BTCAddress]) -> dict[BTCAddress, tuple[bool, FVal]]:
    """
    Takes a list of BCH addresses and returns a mapping of which addresses have had transactions
    and also their current balance

    May raise:
    - RemoteError if any of the queried websites fail to be queried
    """
    try:
        have_transactions = _check_haskoin_for_transactions(accounts)
    except requests.exceptions.RequestException as e:
        raise RemoteError(f'bitcoin cash external API request for transactions failed due to {e!s}') from e  # noqa: E501
    except KeyError as e:
        raise RemoteError(
            f'Malformed response when querying BCH blockchain via {HASKOIN_BASE_URL}. '
            f'Did not find key {e!s}',
        ) from e
    except DeserializationError as e:
        raise RemoteError(
            f'Malformed response when querying BCH blockchain via {HASKOIN_BASE_URL}. '
            'Unable to parse balance.',
        ) from e
    return have_transactions
