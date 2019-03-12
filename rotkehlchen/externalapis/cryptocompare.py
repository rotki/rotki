import logging
import os
from json.decoder import JSONDecodeError
from typing import Any, Dict

from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import FilePath
from rotkehlchen.utils import request_get, rlk_jsondumps, rlk_jsonloads, ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class Cryptocompare():

    def __init__(self, data_directory: FilePath):
        self.prefix = 'https://min-api.cryptocompare.com/data/'
        self.data_directory = data_directory

    def _api_query(self, path: str) -> Dict[str, Any]:
        querystr = f'{self.prefix}{path}'
        log.debug('Querying cryptocompare', url=querystr)
        resp = request_get(querystr)
        if 'Response' not in resp or resp['Response'] != 'Success':
            error_message = 'Failed to query cryptocompare for: "{}"'.format(querystr)
            if 'Message' in resp:
                error_message += ". Error: {}".format(resp['Message'])

            log.error('Cryptocompare query failure', url=querystr, error=error_message)
            raise ValueError(error_message)

        return resp['Data']

    def all_coins(self) -> Dict[str, Any]:
        """Gets the list of all the cryptocompare coins"""
        # Get coin list of crypto compare
        invalidate_cache = True
        coinlist_cache_path = os.path.join(self.data_directory, 'cryptocompare_coinlist.json')
        if os.path.isfile(coinlist_cache_path):
            log.info('Found cryptocompare coinlist cache', path=coinlist_cache_path)
            with open(coinlist_cache_path, 'rb') as f:
                try:
                    data = rlk_jsonloads(f.read())
                    now = ts_now()
                    invalidate_cache = False

                    # If we got a cache and its' over a month old then requery cryptocompare
                    if data['time'] < now and now - data['time'] > 2629800:
                        log.info('Cryptocompare coinlist cache is now invalidated')
                        invalidate_cache = True
                        data = data['data']
                except JSONDecodeError:
                    invalidate_cache = True

        if invalidate_cache:
            data = self._api_query('all/coinlist')

            # Also save the cache
            with open(coinlist_cache_path, 'w') as f:
                now = ts_now()
                log.info('Writing coinlist cache', timestamp=now)
                write_data = {'time': now, 'data': data}
                f.write(rlk_jsondumps(write_data))
        else:
            # in any case take the data
            data = data['data']

        # As described in the docs
        # https://min-api.cryptocompare.com/documentation?key=Other&cat=allCoinsWithContentEndpoint
        # This is not the entire list of assets in the system, so I am manually adding
        # here assets I am aware of that they already have historical data for in thei
        # cryptocompare system
        data['DAO'] = object()
        data['USDT'] = object()
        data['VEN'] = object()
        data['AIR*'] = object()  # This is Aircoin

        return data
