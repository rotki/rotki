#!/usr/bin/env python
import logging
import os
from json.decoder import JSONDecodeError
from typing import Any, Dict, List, Optional, Tuple, Union

import requests
from gevent.lock import Semaphore

from rotkehlchen.constants import CACHE_RESPONSE_FOR_SECS
from rotkehlchen.exchanges.data_structures import AssetMovement
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import ApiKey, ApiSecret, FilePath, T_ApiKey, T_ApiSecret, Timestamp
from rotkehlchen.utils.serialization import rlk_jsondumps, rlk_jsonloads_dict

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def data_up_todate(json_data: Dict[str, Any], start_ts: Timestamp, end_ts: Timestamp) -> bool:
    if 'data' not in json_data or 'start_time' not in json_data or 'end_time' not in json_data:
        return False

    start_ts_ok = (
        (json_data['start_time'] is not None) and
        start_ts >= json_data['start_time']
    )
    end_ts_ok = (
        json_data['end_time'] is not None and
        end_ts <= json_data['end_time']
    )
    return start_ts_ok and end_ts_ok


class ExchangeInterface():

    def __init__(
            self,
            name: str,
            api_key: ApiKey,
            secret: ApiSecret,
            user_directory: FilePath,
    ):
        assert isinstance(api_key, T_ApiKey), (
            'api key for {} should be a bytestring'.format(name)
        )
        assert isinstance(secret, T_ApiSecret), (
            'secret for {} should be a bytestring'.format(name)
        )
        self.name = name
        self.user_directory = user_directory
        self.api_key = api_key
        self.secret = secret
        self.first_connection_made = False
        self.session = requests.session()
        self.session.headers.update({'User-Agent': 'rotkehlchen'})

        # -- Cache related variales
        self.lock = Semaphore()
        self.results_cache: Dict[str, Any] = {}
        # The amount of seconds cache of cache_response_timewise is supposed to last
        # IF 0 is given then cache is disabled. A zero value also disabled the trades cache
        self.cache_ttl_secs = CACHE_RESPONSE_FOR_SECS
        log.info(f'Initialized {name} exchange')

    def _get_cachefile_name(self, special_name: Optional[str] = None) -> str:
        if special_name is None:
            return os.path.join(self.user_directory, "%s_trades.json" % self.name)
        else:
            return os.path.join(self.user_directory, "%s_%s.json" % (self.name, special_name))

    def check_trades_cache(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            special_name: Optional[str] = None,
    ) -> Optional[Union[List[Dict[str, Any]], Dict[str, Any]]]:
        if self.cache_ttl_secs == 0:
            return None

        trades_file = self._get_cachefile_name(special_name)
        trades: Dict[str, Dict[str, Any]] = dict()
        if os.path.isfile(trades_file):
            with open(trades_file, 'r') as f:
                try:
                    trades = rlk_jsonloads_dict(f.read())
                except JSONDecodeError:
                    pass

                # no need to query again
                if data_up_todate(trades, start_ts, end_ts):
                    return trades['data']

        return None

    def check_trades_cache_dict(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            special_name: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        response = self.check_trades_cache(start_ts, end_ts, special_name)
        if not response:
            return None
        assert isinstance(response, Dict)
        return response

    def check_trades_cache_list(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            special_name: Optional[str] = None,
    ) -> Optional[List[Any]]:
        response = self.check_trades_cache(start_ts, end_ts, special_name)
        if not response:
            return None
        assert isinstance(response, List)
        return response

    def update_trades_cache(
            self,
            data: Union[List[Any], Dict[str, Any]],
            start_ts: Timestamp,
            end_ts: Timestamp,
            special_name: Optional[str] = None,
    ) -> None:
        trades_file = self._get_cachefile_name(special_name)
        trades: Dict[str, Union[Timestamp, List[Any], Dict[str, Any]]] = dict()
        with open(trades_file, 'w') as f:
            trades['start_time'] = start_ts
            trades['end_time'] = end_ts
            trades['data'] = data
            f.write(rlk_jsondumps(trades))

    def query_balances(self) -> None:
        """Returns the balances held in the exchange in the following format:
        {
            'name' : {'amount': 1337, 'usd_value': 42},
            'ICN': {'amount': 42, 'usd_value': 1337}
        }

        The name must be the canonical name used by rotkehlchen
        """
        raise NotImplementedError("query_balances should only be implemented by subclasses")

    def query_deposits_withdrawals(
            self,
            start_ts: Timestamp,
            end_ts: Timestamp,
            end_at_least_ts: Timestamp,
    ) -> List[AssetMovement]:
        raise NotImplementedError(
            'query_deposits_withdrawals should only be implemented by subclasses',
        )

    def first_connection(self) -> None:
        """Performs actions that should be done in the first time coming online
        and attempting to query data from an exchange.
        """
        raise NotImplementedError('first_connection() should only be implemented by subclasses')

    def validate_api_key(self) -> Tuple[bool, str]:
        """Tries to make the simplest private api query to the exchange in order to
        verify the api key's validity"""
        raise NotImplementedError('validate_api_key() should only be implemented by subclasses')
