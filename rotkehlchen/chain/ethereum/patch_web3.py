"""
This is just a temporary LRU cache mimicking the behaviour of the _session_cache
https://github.com/ethereum/web3.py/blob/v5.15.0/web3/_utils/request.py#L25
but in a thread-safe way.

Also monkey patches _session_cache to use our LRU cache.

We can get rid of both our class and of the monkey patching once
https://github.com/ethereum/web3.py/issues/1847 is fixed.
"""

from collections import OrderedDict

import requests
from gevent.lock import Semaphore


class TempWeb3LRUCache():

    def __init__(self) -> None:
        self._cache: 'OrderedDict[str, requests.Session]' = OrderedDict()
        self._lock = Semaphore()

    def __setitem__(self, key: str, item: requests.Session) -> None:
        with self._lock:
            if len(self._cache) >= 8:
                _, popped_session = self._cache.popitem(last=False)
                popped_session.close()
            self._cache[key] = item

    def __getitem__(self, key: str) -> requests.Session:
        with self._lock:
            if key not in self._cache:
                raise KeyError

            return self._cache[key]

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._cache


import web3

web3._utils.request._session_cache = TempWeb3LRUCache()
