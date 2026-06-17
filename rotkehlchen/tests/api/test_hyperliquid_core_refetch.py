from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_sync_response_with_result
from rotkehlchen.types import Location, SupportedBlockchain, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(match_on=['uri', 'method', 'body'])
@pytest.mark.parametrize('hyperliquid_accounts', [[string_to_evm_address('0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF')]])  # noqa: E501
def test_refetch_hyperliquid_core_history_with_max_event(
        rotkehlchen_api_server: 'APIServer',
        hyperliquid_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Regression test for force-refetching Hyperliquid core history.

    Uses the cassette from the shared test cache directory under
    `~/Library/Application Support/rotki/test-caching/cassettes`.
    """
    address = hyperliquid_accounts[0]
    from_timestamp = Timestamp(1781308800)  # 2026-06-13 00:00:00 UTC
    to_timestamp = Timestamp(1781395199)  # 2026-06-13 23:59:59 UTC

    with patch(
        'rotkehlchen.chain.evm.transactions.EvmTransactions.refetch_transactions_for_address',
        return_value=[],
    ):
        first_result = assert_proper_sync_response_with_result(requests.post(
            api_url_for(rotkehlchen_api_server, 'refetchtransactionsresource'),
            json={
                'async_query': False,
                'from_timestamp': from_timestamp,
                'to_timestamp': to_timestamp,
                'chain': SupportedBlockchain.HYPERLIQUID.serialize(),
                'address': address,
            },
        ))
        second_result = assert_proper_sync_response_with_result(requests.post(
            api_url_for(rotkehlchen_api_server, 'refetchtransactionsresource'),
            json={
                'async_query': False,
                'from_timestamp': from_timestamp,
                'to_timestamp': to_timestamp,
                'chain': SupportedBlockchain.HYPERLIQUID.serialize(),
                'address': address,
            },
        ))

    assert first_result == {
        'new_transactions': {},
        'new_transactions_count': 0,
        'new_history_events_count': 1,
    }
    assert second_result == {
        'new_transactions': {},
        'new_transactions_count': 0,
        'new_history_events_count': 0,
    }

    with rotkehlchen_api_server.rest_api.rotkehlchen.data.db.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM history_events WHERE location=? AND location_label=? '
            'AND asset=? AND timestamp=?',
            (
                Location.HYPERLIQUID.serialize_for_db(),
                address,
                Asset('MAX').identifier,
                1781377469380,
            ),
        ).fetchone()[0] == 1
