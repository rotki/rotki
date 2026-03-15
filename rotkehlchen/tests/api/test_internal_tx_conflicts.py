from typing import TYPE_CHECKING

import requests

from rotkehlchen.db.internal_tx_conflicts import (
    INTERNAL_TX_CONFLICT_ACTION_FIX_REDECODE,
    INTERNAL_TX_CONFLICT_ACTION_REPULL,
)
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response_with_result
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


def test_get_pending_internal_tx_conflicts_endpoint(rotkehlchen_api_server: 'APIServer') -> None:
    tx_hash_pending = make_evm_tx_hash()
    tx_hash_done = make_evm_tx_hash()
    tx_hash_other_action = make_evm_tx_hash()
    with rotkehlchen_api_server.rest_api.rotkehlchen.data.db.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO evm_internal_tx_conflicts(transaction_hash, chain, action, fixed) VALUES (?, ?, ?, ?)',  # noqa: E501
            [
                (tx_hash_pending, ChainID.ETHEREUM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_REPULL, 0),  # noqa: E501
                (tx_hash_done, ChainID.ETHEREUM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_REPULL, 1),  # noqa: E501
                (tx_hash_other_action, ChainID.ETHEREUM.serialize_for_db(), INTERNAL_TX_CONFLICT_ACTION_FIX_REDECODE, 0),  # noqa: E501
            ],
        )

    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'internaltxconflictsresource'),
        json={'async_query': False},
    )
    result = assert_proper_response_with_result(
        response=response,
        rotkehlchen_api_server=rotkehlchen_api_server,
        async_query=False,
    )
    assert result == [{'chain': 'ethereum', 'tx_hash': str(tx_hash_pending)}]
