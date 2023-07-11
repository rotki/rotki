import pytest
import requests

from rotkehlchen.db.settings import CachedSettings


class ConfigurableSession(requests.Session):
    """A configurable requests Session that can be used anywhere"""

    def __init__(self, timeout):
        super().__init__()
        self.timeout = timeout

    def request(
            self,
            method,
            url,
            params=None,
            data=None,
            headers=None,
            cookies=None,
            files=None,
            auth=None,
            timeout=None,
            allow_redirects=True,
            proxies=None,
            hooks=None,
            stream=None,
            verify=None,
            cert=None,
            json=None,
    ):
        if timeout is None:
            timeout = self.timeout

        return super().request(
            method=method,
            url=url,
            params=params,
            data=data,
            headers=headers,
            cookies=cookies,
            files=files,
            auth=auth,
            timeout=timeout,
            allow_redirects=allow_redirects,
            proxies=proxies,
            hooks=hooks,
            stream=stream,
            verify=verify,
            cert=cert,
            json=json,
        )


@pytest.fixture(name='test_timeout')
def fixture_test_timeout():
    return CachedSettings().get_timeout_tuple()


@pytest.fixture(name='test_session_pool_maxsize')
def fixture_test_session_pool_maxsize():
    return 100


@pytest.fixture(name='test_session')
def fixture_test_session(test_timeout, test_session_pool_maxsize):
    """This is a configurable session that can be used in tests instead of pure requests

    What it adds over pure requests is that you get:
    - Automatic and immediate cleanup of all session's connections
    - Configurable connection pool size. Default setup is 10x the normal requests default.
    - Configurable but also default timeout without specifying it in all requests.

    The downside is that all that may slow the test this is used by a tiny bit and higher
    pool size naturally uses more memory.
    """
    with ConfigurableSession(timeout=test_timeout) as session:
        adapter = requests.adapters.HTTPAdapter(pool_maxsize=test_session_pool_maxsize)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        yield session
