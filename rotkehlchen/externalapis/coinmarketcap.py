import logging
import os
from json.decoder import JSONDecodeError
from typing import Any, Dict, List

import gevent
import requests

from rotkehlchen.errors import RemoteError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import FilePath
from rotkehlchen.utils import rlk_jsondumps, rlk_jsonloads, rlk_jsonloads_dict, ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

INITIAL_BACKOFF = 5

# There can be multiple ids for the same symbol and for cases such as this
# we use this mapping to manually map Rotkehlchen symbols to CMC IDs
WORLD_TO_CMC_ID = {
    # Bitstars
    'BITS': 276,
    # Bitswift
    'BITS-2': 659,
    # Bitmark
    'BTM': 543,
    # Bytom
    'BTM-2': 1866,
}


class Coinmarketcap():

    def __init__(self, data_directory: FilePath, api_key: str):
        self.prefix = 'https://pro-api.coinmarketcap.com/'
        self.backoff_limit = 180
        self.data_directory = data_directory
        self.session = requests.session()
        # As per coinmarketcap's API
        self.session.headers.update({
            'User-Agent': 'rotkehlchen',
            'X-CMC_PRO_API_KEY': api_key,
            'Accept': 'application/json',
            'Accept-Encoding': 'deflate, gzip',
        })

    def _query(self, path: str) -> str:
        backoff = INITIAL_BACKOFF
        while True:
            response = self.session.get(f'{self.prefix}{path}')
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

    def _get_cryptocyrrency_map(self) -> List[Dict[str, Any]]:
        start = 1
        limit = 5000
        result = []
        while True:
            response_data = rlk_jsonloads_dict(
                self._query(f'v1/cryptocurrency/map?start={start}&limit={limit}'),
            )
            result.extend(response_data['data'])
            if len(response_data['data']) != limit:
                break

        return result

    def get_cryptocyrrency_map(self) -> List[Dict[str, Any]]:
        # TODO: Both here and in cryptocompare the cache funcionality is the same
        # Extract the caching part into its own function somehow and abstract it
        # away
        invalidate_cache = True
        coinlist_cache_path = os.path.join(self.data_directory, 'cmc_coinlist.json')
        if os.path.isfile(coinlist_cache_path):
            log.info('Found coinmarketcap coinlist cache', path=coinlist_cache_path)
            with open(coinlist_cache_path, 'rb') as f:
                try:
                    data = rlk_jsonloads(f.read())
                    now = ts_now()
                    invalidate_cache = False

                    # If we got a cache and its' over a month old then requery coinmarketcap
                    if data['time'] < now and now - data['time'] > 2629800:
                        log.info('Coinmarketcap coinlist cache is now invalidated')
                        invalidate_cache = True
                        data = data['data']
                except JSONDecodeError:
                    invalidate_cache = True

        if invalidate_cache:
            data = self._get_cryptocyrrency_map()
            # Also save the cache
            with open(coinlist_cache_path, 'w') as f:
                now = ts_now()
                log.info('Writing coinmarketcap coinlist cache', timestamp=now)
                write_data = {'time': now, 'data': data}
                f.write(rlk_jsondumps(write_data))
        else:
            # in any case take the data
            data = data['data']

        return data
