import json
import warnings as test_warnings
from unittest.mock import patch

import pytest

from rotkehlchen.chain.evm.types import (
    EvmIndexer,
)
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.externalapis.routescan import ROUTESCAN_SUPPORTED_CHAINS
from rotkehlchen.types import ChainID, ExternalService
from rotkehlchen.utils.misc import ts_now


@pytest.fixture(name='gnosispay_credentials')
def fixture_gnosispay_credentials(database):
    """Input mock monerium credentials to the DB for testing"""
    with database.user_write() as write_cursor:
        write_cursor.execute(
            'INSERT OR REPLACE INTO external_service_credentials(name, api_key, api_secret) '
            'VALUES(?, ?, ?)',
            (ExternalService.GNOSIS_PAY.name.lower(), 'token', None),
        )


@pytest.fixture(name='monerium_credentials')
def fixture_monerium_credentials(database):
    """Input mock monerium credentials to the DB for testing"""
    with database.user_write() as write_cursor:
        database.set_static_cache(
            write_cursor=write_cursor,
            name=DBCacheStatic.MONERIUM_OAUTH_CREDENTIALS,
            value=json.dumps({
                'access_token': 'mock-access-token',
                'refresh_token': 'mock-refresh-token',
                'expires_at': ts_now() + 3600,
                'client_id': 'mock-client-id',
                'token_type': 'Bearer',
                'user_email': 'mock@monerium.com',
            }),
        )


@pytest.fixture(name='allow_base_routescan')
def fixture_allow_base_routescan():
    """Routescan no longer fully indexes Base, so we've removed it from its supported chains to
    avoid quietly missing new transactions. But as of 2026/02/13 Blockscout (the only other indexer
    supporting Base on free tier), is in the process of some db migrations, and internal tx queries
    may result in errors in some cases. So this is a temporary fixture to allow the tests where
    this internal tx error happens to continue using routescan.
    # TODO: Remove this once Blockscout is finished with their db migrations.
    """
    test_warnings.warn(UserWarning('Temporarily allowing Routescan for Base'))
    with patch(
        target='rotkehlchen.externalapis.routescan.ROUTESCAN_SUPPORTED_CHAINS',
        new=ROUTESCAN_SUPPORTED_CHAINS + (ChainID.BASE,),
    ):
        yield


@pytest.fixture(name='allow_scroll_etherscan')
def fixture_allow_scroll_etherscan():
    """Etherscan no longer supports Scroll, so we've removed it from its supported chains.
    Let's use this fixture to not fail old recorded tests. Can remove if we re-record
    all tests that have this fixture.
    """
    test_warnings.warn(UserWarning('Temporarily allowing Etherscan for Scroll'))
    cached = CachedSettings()
    new_order = {**cached._evm_indexers_order_per_chain, ChainID.SCROLL: (EvmIndexer.ETHERSCAN,)}
    with patch.object(type(cached), '_evm_indexers_order_per_chain', new_order):
        yield
