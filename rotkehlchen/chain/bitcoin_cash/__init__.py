from typing import Dict, List

import requests

from rotkehlchen.chain.bitcoin_cash.utils import cash_to_legacy_address
from rotkehlchen.errors.misc import RemoteError, UnableToDecryptRemoteData
from rotkehlchen.fval import FVal
from rotkehlchen.types import BTCAddress
from rotkehlchen.utils.misc import satoshis_to_btc
from rotkehlchen.utils.network import request_get


def get_bitcoin_cash_addresses_balances(accounts: List[BTCAddress]) -> Dict[BTCAddress, FVal]:
    """Queries api.haskoin.com for the balances of BCH accounts.

    May raise:
    - RemoteError if there is a problem querying api.haskoin.com
    """
    source = 'https://api.haskoin.com'
    balances: Dict[BTCAddress, FVal] = {}
    try:
        accounts_chunks = [accounts[x:x + 80] for x in range(0, len(accounts), 80)]
        for accounts_chunk in accounts_chunks:
            params = ','.join(accounts_chunk)
            bch_resp = request_get(url=f'{source}/bch/address/balances?addresses={params}')
            for entry in bch_resp:
                # Try and get the initial address passed to the request.
                # The API returns only CashAddr format addresses
                try:
                    accounts_chunk.index(entry['address'])
                    balances[entry['address']] = satoshis_to_btc(FVal(entry['confirmed']))
                except ValueError:
                    address = cash_to_legacy_address(entry['address'])
                    if address is not None:
                        balances[address] = satoshis_to_btc(FVal(entry['confirmed']))  # noqa: 501
    except (
            requests.exceptions.RequestException,
            UnableToDecryptRemoteData,
            requests.exceptions.Timeout,
    ) as e:
        raise RemoteError(f'Bitcoin Cash external API request for balances failed due to {str(e)}') from e  # noqa: E501
    except KeyError as e:
        raise RemoteError(
            f'Malformed response when querying Bitcoin Cash blockchain via {source}.'
            f'Did not find key {e}',
        ) from e

    return balances
