import json
import warnings as test_warnings
from contextlib import contextmanager
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.chain.evm.types import DEFAULT_INDEXERS_ORDER, EvmIndexer
from rotkehlchen.db.cache import DBCacheStatic
from rotkehlchen.db.settings import CachedSettings
from rotkehlchen.externalapis.routescan import ROUTESCAN_SUPPORTED_CHAINS
from rotkehlchen.types import ChainID, ExternalService
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from collections.abc import Iterator


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


@contextmanager
def _allow_routescan(chain: ChainID) -> Iterator[None]:
    """Let Routescan serve a chain it no longer supports, in the indexer order it had back then.

    Used by the fixtures below to keep cassettes recorded while Routescan served the chain
    replayable. Restoring its support alone is not enough, since the chain's default order no
    longer lists it and the queries would go straight to the next indexer instead.
    """
    test_warnings.warn(UserWarning(f'Temporarily allowing Routescan for {chain.to_name()}'))
    cached = CachedSettings()
    try:
        with (
            patch(
                target='rotkehlchen.externalapis.routescan.ROUTESCAN_SUPPORTED_CHAINS',
                new=ROUTESCAN_SUPPORTED_CHAINS + (chain,),
            ),
            patch.dict(DEFAULT_INDEXERS_ORDER.order, {chain: (
                EvmIndexer.BLOCKSCOUT,
                EvmIndexer.ROUTESCAN,
                EvmIndexer.ETHERSCAN,
            )}),
        ):
            cached._refresh_indexers_cache()
            yield
    finally:
        cached._refresh_indexers_cache()


@pytest.fixture(name='allow_base_routescan')
def fixture_allow_base_routescan():
    """Routescan no longer fully indexes Base, so we've removed it from its supported chains to
    avoid quietly missing new transactions. But as of 2026/02/13 Blockscout (the only other indexer
    supporting Base on free tier), is in the process of some db migrations, and internal tx queries
    may result in errors in some cases. So this is a temporary fixture to allow the tests where
    this internal tx error happens to continue using routescan.
    # TODO: Remove this once Blockscout is finished with their db migrations.
    """
    with _allow_routescan(ChainID.BASE):
        yield


@pytest.fixture(name='allow_optimism_routescan')
def fixture_allow_optimism_routescan():
    """Routescan stopped serving Optimism, so it was removed from its supported chains and from
    the default Optimism indexer order. This fixture keeps the cassettes recorded before that
    replayable. Can remove if we re-record all tests that have it.
    """
    with _allow_routescan(ChainID.OPTIMISM):
        yield


@contextmanager
def _force_etherscan_indexer(chain: ChainID) -> Iterator[None]:
    """Pin a chain to etherscan regardless of the configured indexer order.

    Used by the fixtures below to keep cassettes recorded back when etherscan was the chain's
    primary indexer replayable after the default moved elsewhere.
    """
    test_warnings.warn(UserWarning(f'Temporarily allowing Etherscan for {chain.to_name()}'))
    cached = CachedSettings()
    new_order = {**cached._evm_indexers_order_per_chain, chain: (EvmIndexer.ETHERSCAN,)}
    with patch.object(type(cached), '_evm_indexers_order_per_chain', new_order):
        yield


@pytest.fixture(name='allow_scroll_etherscan')
def fixture_allow_scroll_etherscan():
    """Etherscan no longer supports Scroll, so we've removed it from its supported chains.
    Let's use this fixture to not fail old recorded tests. Can remove if we re-record
    all tests that have this fixture.
    """
    with _force_etherscan_indexer(ChainID.SCROLL):
        yield


@pytest.fixture(name='allow_gnosis_etherscan')
def fixture_allow_gnosis_etherscan():
    """Etherscan only serves Gnosis to paid api keys now, so blockscout became the primary
    gnosis indexer. Every gnosis cassette predates that and is recorded against etherscan, so
    this fixture keeps them replayable. Can remove if we re-record all tests that have it.
    """
    with _force_etherscan_indexer(ChainID.GNOSIS):
        yield
