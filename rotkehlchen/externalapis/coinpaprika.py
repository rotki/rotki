from typing import Any, Dict, List

import gevent
import requests

from rotkehlchen.errors import RemoteError
from rotkehlchen.utils import rlk_jsonloads_dict, rlk_jsonloads_list

INITIAL_BACKOFF = 3


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
