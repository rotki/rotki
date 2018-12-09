#!/usr/bin/env python
import logging
import os
from json.decoder import JSONDecodeError
from typing import Dict, List, Optional, Union

import requests
from gevent.lock import Semaphore

from rotkehlchen import typing
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.utils import rlk_jsondumps, rlk_jsonloads

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


def data_up_todate(json_data: dict, start_ts: typing.Timestamp, end_ts: typing.Timestamp) -> bool:
    if 'data' not in json_data or 'start_time' not in json_data or 'end_time' not in json_data:
        return False

    start_ts_ok = (
        (start_ts is not None and json_data['start_time'] is not None) and
        start_ts >= json_data['start_time']
    )
    end_ts_ok = (
        end_ts is not None and json_data['end_time'] is not None and
        end_ts <= json_data['end_time']
    )
    return start_ts_ok and end_ts_ok


class Exchange(object):

    def __init__(
            self,
            name: str,
            api_key: typing.ApiKey,
            secret: typing.ApiSecret,
            user_directory: typing.FilePath,
    ):
        assert isinstance(api_key, typing.T_ApiKey), (
            'api key for {} should be a bytestring'.format(name)
        )
        assert isinstance(secret, typing.T_ApiSecret), (
            'secret for {} should be a bytestring'.format(name)
        )
        self.name = name
        self.user_directory = user_directory
        self.api_key = api_key
        self.secret = secret
        self.first_connection_made = False
        self.session = requests.session()
        self.lock = Semaphore()
        self.results_cache: dict = {}
        self.session.headers.update({'User-Agent': 'rotkehlchen'})
        log.info(f'Initialized {name} exchange')

    def _get_cachefile_name(self, special_name: str = None) -> str:
        if special_name is None:
            return os.path.join(self.user_directory, "%s_trades.json" % self.name)
        else:
            return os.path.join(self.user_directory, "%s_%s.json" % (self.name, special_name))

    def check_trades_cache(
            self,
            start_ts: typing.Timestamp,
            end_ts: typing.Timestamp,
            special_name: str = None,
    ) -> Optional[Union[List, Dict]]:
        trades_file = self._get_cachefile_name(special_name)
        trades: dict = dict()
        if os.path.isfile(trades_file):
            with open(trades_file, 'r') as f:
                try:
                    trades = rlk_jsonloads(f.read())
                except JSONDecodeError:
                    pass

                # no need to query again
                if data_up_todate(trades, start_ts, end_ts):
                    return trades['data']

        return None

    def update_trades_cache(
            self,
            data: Union[List, Dict],
            start_ts: typing.Timestamp,
            end_ts: typing.Timestamp,
            special_name: str = None,
    ) -> None:
        trades_file = self._get_cachefile_name(special_name)
        trades: Dict[str, Union[typing.Timestamp, List, Dict]] = dict()
        with open(trades_file, 'w') as f:
            trades['start_time'] = start_ts
            trades['end_time'] = end_ts
            trades['data'] = data
            f.write(rlk_jsondumps(trades))

    def query_balances(self):
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
            start_ts: typing.Timestamp,
            end_ts: typing.Timestamp,
            end_at_least_ts: typing.Timestamp,
    ):
        raise NotImplementedError(
            'query_deposits_withdrawals should only be implemented by subclasses',
        )

    def first_connection(self):
        """Performs actions that should be done in the first time coming online
        and attempting to query data from an exchange.
        """
        raise NotImplementedError('first_connection() should only be implemented by subclasses')

    def validate_api_key(self):
        """Tries to make the simplest private api query to the exchange in order to
        verify the api key's validity"""
        raise NotImplementedError('validate_api_key() should only be implemented by subclasses')
