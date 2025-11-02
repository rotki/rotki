from http import HTTPStatus
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.ethereum.modules.lido_csm.constants import LidoCsmOperatorType
from rotkehlchen.chain.ethereum.modules.lido_csm.metrics import LidoCsmNodeOperatorStats
from rotkehlchen.db.lido_csm import DBLidoCsm
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import SupportedBlockchain


@pytest.fixture(name='metrics_payload')
def _patched_metrics_fetcher_session():
    stats = LidoCsmNodeOperatorStats(
        operator_type=LidoCsmOperatorType.PERMISSIONLESS,
        current_bond=FVal('1.0'),
        required_bond=FVal('2.0'),
        claimable_bond=FVal('0.5'),
        total_deposited_validators=42,
        rewards_steth=FVal('0.3'),
    )
    with patch(
        'rotkehlchen.api.rest.LidoCsmMetricsFetcher.get_operator_stats',
        return_value=stats,
    ):
        yield stats.serialize()


def _register_eth_account(rotki, address) -> None:
    with rotki.data.db.user_write() as cursor:
        rotki.data.db.add_blockchain_accounts(
            write_cursor=cursor,
            account_data=[BlockchainAccountData(
                chain=SupportedBlockchain.ETHEREUM,
                address=address,
            )],
        )


def test_get_lido_csm_node_operators(rotkehlchen_api_server) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBLidoCsm(rotki.data.db)

    address = make_evm_address()
    _register_eth_account(rotki, address)
    db.add_node_operator(
        address=address,
        node_operator_id=5,
    )
    stats = LidoCsmNodeOperatorStats(
        operator_type=LidoCsmOperatorType.PERMISSIONLESS,
        current_bond=FVal('1.0'),
        required_bond=FVal('2.0'),
        claimable_bond=FVal('0.5'),
        total_deposited_validators=42,
        rewards_steth=FVal('0.3'),
    )
    db.set_metrics(node_operator_id=5, metrics=stats)
    expected_metrics = stats.serialize()

    result = assert_proper_sync_response_with_result(
        requests.get(api_url_for(rotkehlchen_api_server, 'lidocsmnodeoperatorresource')),
    )

    assert result == [{
        'address': address,
        'node_operator_id': 5,
        'metrics': expected_metrics,
    }]


def test_add_lido_csm_node_operator(
        rotkehlchen_api_server,
        metrics_payload,
) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBLidoCsm(rotki.data.db)

    address = make_evm_address()
    _register_eth_account(rotki, address)
    result = assert_proper_sync_response_with_result(
        requests.put(
            api_url_for(rotkehlchen_api_server, 'lidocsmnodeoperatorresource'),
            json={
                'address': address,
                'node_operator_id': 10,
            },
        ),
    )
    assert len(result) == 1
    assert result[0]['node_operator_id'] == 10
    assert result[0]['metrics'] == metrics_payload

    entries = db.get_node_operators()
    assert len(entries) == 1
    assert entries[0].node_operator_id == 10
    assert entries[0].metrics is not None
    assert entries[0].metrics.serialize() == metrics_payload


def test_add_lido_csm_node_operator_requires_tracked_account(
        rotkehlchen_api_server,
) -> None:
    address = make_evm_address()
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'lidocsmnodeoperatorresource'),
        json={
            'address': address,
            'node_operator_id': 11,
        },
    )
    assert_error_response(
        response,
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg='not registered as an Ethereum EVM account',
    )


def test_delete_lido_csm_node_operator(rotkehlchen_api_server) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBLidoCsm(rotki.data.db)

    address = make_evm_address()
    _register_eth_account(rotki, address)
    db.add_node_operator(
        address=address,
        node_operator_id=3,
    )

    result = assert_proper_sync_response_with_result(
        requests.delete(
            api_url_for(rotkehlchen_api_server, 'lidocsmnodeoperatorresource'),
            json={
                'address': address,
                'node_operator_id': 3,
            },
        ),
    )
    assert result == []
    assert db.get_node_operators() == ()


def test_refresh_metrics_endpoint_persists(
        rotkehlchen_api_server,
        metrics_payload,
) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBLidoCsm(rotki.data.db)
    address = make_evm_address()
    _register_eth_account(rotki, address)
    db.add_node_operator(
        address=address,
        node_operator_id=7,
    )

    result = assert_proper_sync_response_with_result(
        requests.post(api_url_for(rotkehlchen_api_server, 'lidocsmmetricsresource')),
    )
    assert len(result) == 1
    assert result[0]['node_operator_id'] == 7
    assert result[0]['metrics'] == metrics_payload

    entries = db.get_node_operators()
    assert len(entries) == 1
    assert entries[0].node_operator_id == 7
    assert entries[0].metrics is not None
    assert entries[0].metrics.serialize() == metrics_payload


def test_add_lido_csm_node_operator_returns_warning_on_metrics_failure(
        rotkehlchen_api_server,
) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    address = make_evm_address()
    _register_eth_account(rotki, address)

    with patch(
        'rotkehlchen.api.rest.LidoCsmMetricsFetcher.get_operator_stats',
        side_effect=RemoteError('boom'),
    ):
        response = requests.put(
            api_url_for(rotkehlchen_api_server, 'lidocsmnodeoperatorresource'),
            json={
                'address': address,
                'node_operator_id': 12,
            },
        )

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    payload = response.json()
    assert payload['result'][0]['metrics'] is None
    assert 'Failed to fetch metrics' in payload['message']


def test_refresh_metrics_endpoint_warns_on_failure(rotkehlchen_api_server) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBLidoCsm(rotki.data.db)
    address = make_evm_address()
    _register_eth_account(rotki, address)
    db.add_node_operator(
        address=address,
        node_operator_id=7,
    )

    with patch(
        'rotkehlchen.api.rest.LidoCsmMetricsFetcher.get_operator_stats',
        side_effect=RemoteError('boom'),
    ):
        response = requests.post(api_url_for(rotkehlchen_api_server, 'lidocsmmetricsresource'))

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    payload = response.json()
    assert payload['result'][0]['metrics'] is None
    assert '7' in payload['message']
