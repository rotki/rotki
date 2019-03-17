from typing import Any, Dict, List

import gevent
import requests

from rotkehlchen.errors import RemoteError
from rotkehlchen.utils import rlk_jsonloads_dict, rlk_jsonloads_list

INITIAL_BACKOFF = 3

# Some symbols in coin paprika exists multiple times with different ids each time.
# This requires manual intervention and a lock in of the id mapping by hand
WORLD_TO_PAPRIKA_ID = {
    # ICN has both icn-iconomi and icn-icoin. The correct one appears to be the first
    'ICN': 'icn-iconomi',
    # In Rotkehlchen BAT means the basic attention token and not bat-batcoin
    'BAT': 'bat-basic-attention-token',
    # For Rotkehlchen BITS is Bitstars and not Bitswift
    'BITS': 'bits-bitstar',
    # And then naturally BITS-2 is Bitswift
    'BITS-2': 'bits-bitswift',
    # For Rotkehlchen BTCS is BitcoinScrypt
    'BTCS': 'btcs-bitcoin-scrypt',
    # For Rotkehlchen BTM is Bitmark
    'BTM': 'btm-bitmark',
    # For Rotkehlchen BTM-2 is Bytom
    'BTM-2': 'btm-bytom',
    # For Rotkehlchen CCN is CustomContractNetwork
    'CCN': 'ccn-customcontractnetwork',
    # For Rotkehlchen CCN-2 is Cannacoin
    'CCN-2': 'ccn-cannacoin',
    # For Rotkehlchen CYC is conspiracy coin, but in paprika it's
    # known as cycling coin, so mark it as unknown mapping
    'CYC': None,
    # For Rotkehlchen FAIR is FairCoin
    'FAIR': 'fair-faircoin',
    # For Rotkehlchen FAIR-2 is FairGame
    'FAIR-2': 'fair-fairgame',
}


class CoinPaprika():

    def __init__(self):
        self.prefix = 'https://api.coinpaprika.com/v1/'
        self.backoff_limit = 180

    def _query(self, path: str) -> str:
        backoff = INITIAL_BACKOFF
        while True:
            response = requests.get(f'{self.prefix}{path}')
            if response.status_code == 429 and backoff < self.backoff_limit:
                gevent.sleep(backoff)
                backoff *= 2
                continue
            elif response.status_code != 200:
                raise RemoteError(
                    f'Coinpaprika API request {response.url} for {path} failed '
                    f'with HTTP status code {response.status_code} and text '
                    f'{response.text}',
                )

            return response.text

    def get_coins_list(self) -> List[Dict[str, Any]]:
        response_data = self._query('coins')
        return rlk_jsonloads_list(response_data)

    def get_coin_by_id(self, coinpaprika_id: str) -> Dict[str, Any]:
        response_data = self._query(f'coins/{coinpaprika_id}')
        return rlk_jsonloads_dict(response_data)
