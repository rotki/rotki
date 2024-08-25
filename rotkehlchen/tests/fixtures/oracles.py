import pytest


@pytest.fixture(name='coingecko_cache_coinlist')
def fixture_coingecko_cache_coinlist():
    """
    # pytest-deadfixtures ignore
    ^^^ this allows our fork of pytest-deadfixtures to ignore this fixture for usage detection
    since at least for now in the tests the default None value is never used
    """
    return None


@pytest.fixture(name='cryptocompare_cache_coinlist')
def fixture_cryptocompare_cache_coinlist():
    return None


@pytest.fixture(name='cache_coinlist')
def fixture_cache_coinlist(rotkehlchen_api_server, coingecko_cache_coinlist, cryptocompare_cache_coinlist) -> None:  # noqa: E501
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    if cryptocompare_cache_coinlist is not None:
        rotki.cryptocompare.cache_coinlist(cryptocompare_cache_coinlist)
    if coingecko_cache_coinlist is not None:
        rotki.coingecko.cache_coinlist(coingecko_cache_coinlist)
