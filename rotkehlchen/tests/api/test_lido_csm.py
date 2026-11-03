from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.ethereum.modules.lido_csm.constants import (
    LidoCsmOperatorType,
    LidoCsmStakingModule,
)
from rotkehlchen.chain.ethereum.modules.lido_csm.metrics import (
    LidoCsmMetricsFetcher,
    LidoCsmNodeOperatorStats,
)
from rotkehlchen.db.lido_csm import DBLidoCsm
from rotkehlchen.errors.cause import FailureCause
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import SupportedBlockchain

if TYPE_CHECKING:
    from collections.abc import Iterator

    from rotkehlchen.api.server import APIServer
    from rotkehlchen.rotkehlchen import Rotkehlchen
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.fixture(name='metrics_payload')
def _patched_metrics_fetcher_session() -> Iterator[dict[str, Any]]:
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


def _register_eth_account(rotki: Rotkehlchen, address: ChecksumEvmAddress) -> None:
    with rotki.data.db.user_write() as cursor:
        rotki.data.db.add_blockchain_accounts(
            write_cursor=cursor,
            account_data=[BlockchainAccountData(
                chain=SupportedBlockchain.ETHEREUM,
                address=address,
            )],
        )


def test_get_lido_csm_node_operators(rotkehlchen_api_server: APIServer) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBLidoCsm(rotki.data.db)

    _register_eth_account(rotki, (address := make_evm_address()))
    db.add_node_operator(
        address=address,
        node_operator_id=5,
        staking_module=LidoCsmStakingModule.CSM,
    )
    stats = LidoCsmNodeOperatorStats(
        operator_type=LidoCsmOperatorType.PERMISSIONLESS,
        current_bond=FVal('1.0'),
        required_bond=FVal('2.0'),
        claimable_bond=FVal('0.5'),
        total_deposited_validators=42,
        rewards_steth=FVal('0.3'),
    )
    db.set_metrics(node_operator_id=5, metrics=stats, staking_module=LidoCsmStakingModule.CSM)

    assert assert_proper_sync_response_with_result(
        requests.get(api_url_for(rotkehlchen_api_server, 'lidocsmnodeoperatorresource')),
    ) == [{
        'address': address,
        'node_operator_id': 5,
        'staking_module_id': 3,
        'metrics': stats.serialize(),
    }]


def test_add_lido_csm_node_operator(
        rotkehlchen_api_server: APIServer,
        metrics_payload: dict[str, Any],
) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    _register_eth_account(rotki, (address := make_evm_address()))
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
    assert result[0]['staking_module_id'] == LidoCsmStakingModule.CSM.value
    assert result[0]['metrics'] == metrics_payload

    entries = DBLidoCsm(rotki.data.db).get_node_operators()
    assert len(entries) == 1
    assert entries[0].node_operator_id == 10
    assert entries[0].staking_module == LidoCsmStakingModule.CSM
    assert entries[0].metrics is not None
    assert entries[0].metrics.serialize() == metrics_payload


def test_add_lido_csm_node_operator_requires_tracked_account(
        rotkehlchen_api_server: APIServer,
) -> None:
    assert_error_response(
        requests.put(
            api_url_for(rotkehlchen_api_server, 'lidocsmnodeoperatorresource'),
            json={
                'address': make_evm_address(),
                'node_operator_id': 11,
            },
        ),
        status_code=HTTPStatus.CONFLICT,
        contained_in_msg='not registered as an Ethereum EVM account',
    )


def test_delete_lido_csm_node_operator(rotkehlchen_api_server: APIServer) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBLidoCsm(rotki.data.db)

    _register_eth_account(rotki, (address := make_evm_address()))
    db.add_node_operator(
        address=address,
        node_operator_id=3,
        staking_module=LidoCsmStakingModule.CSM,
    )

    assert assert_proper_sync_response_with_result(
        requests.delete(
            api_url_for(rotkehlchen_api_server, 'lidocsmnodeoperatorresource'),
            json={
                'address': address,
                'node_operator_id': 3,
            },
        ),
    ) == []
    assert db.get_node_operators() == ()


def test_refresh_metrics_endpoint_persists(
        rotkehlchen_api_server: APIServer,
        metrics_payload: dict[str, Any],
) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBLidoCsm(rotki.data.db)
    _register_eth_account(rotki, (address := make_evm_address()))
    db.add_node_operator(
        address=address,
        node_operator_id=7,
        staking_module=LidoCsmStakingModule.CSM,
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
        rotkehlchen_api_server: APIServer,
) -> None:
    _register_eth_account(
        rotki=rotkehlchen_api_server.rest_api.rotkehlchen,
        address=(address := make_evm_address()),
    )

    with patch(
        'rotkehlchen.api.rest.LidoCsmMetricsFetcher.get_operator_stats',
        side_effect=RemoteError('boom', cause=FailureCause.NETWORK),
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
    assert 'Failed to fetch metrics for node operator CSM #12' in payload['message']


def test_refresh_metrics_endpoint_warns_on_failure(rotkehlchen_api_server: APIServer) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    _register_eth_account(rotki, (address := make_evm_address()))
    DBLidoCsm(rotki.data.db).add_node_operator(
        address=address,
        node_operator_id=7,
        staking_module=LidoCsmStakingModule.CSM,
    )

    with patch(
        'rotkehlchen.api.rest.LidoCsmMetricsFetcher.get_operator_stats',
        side_effect=RemoteError('boom', cause=FailureCause.REMOTE_REJECTED),
    ):
        response = requests.post(api_url_for(rotkehlchen_api_server, 'lidocsmmetricsresource'))

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    payload = response.json()
    assert payload['cause'] == FailureCause.REMOTE_REJECTED
    assert payload['result'][0]['metrics'] is None
    assert '7' in payload['message']


def test_lido_csm_0x02_node_operator_round_trip(
        rotkehlchen_api_server: APIServer,
        metrics_payload: dict[str, Any],
) -> None:
    """CSM 0x02 numbers its operators separately, so its operator 1 does not clash with CSM's"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    _register_eth_account(rotki, (address := make_evm_address()))
    DBLidoCsm(rotki.data.db).add_node_operator(
        address=address,
        node_operator_id=1,
        staking_module=LidoCsmStakingModule.CSM,
    )

    assert assert_proper_sync_response_with_result(
        requests.put(
            api_url_for(rotkehlchen_api_server, 'lidocsmnodeoperatorresource'),
            json={'address': address, 'node_operator_id': 1, 'staking_module_id': 5},
        ),
    ) == [
        {'address': address, 'node_operator_id': 1, 'staking_module_id': 3, 'metrics': None},
        {
            'address': address,
            'node_operator_id': 1,
            'staking_module_id': 5,
            'metrics': metrics_payload,
        },
    ]

    assert assert_proper_sync_response_with_result(
        requests.delete(
            api_url_for(rotkehlchen_api_server, 'lidocsmnodeoperatorresource'),
            json={'address': address, 'node_operator_id': 1, 'staking_module_id': 5},
        ),
    ) == [
        {'address': address, 'node_operator_id': 1, 'staking_module_id': 3, 'metrics': None},
    ]


def test_refresh_metrics_uses_fetcher_of_each_staking_module(
        rotkehlchen_api_server: APIServer,
) -> None:
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = DBLidoCsm(rotki.data.db)
    _register_eth_account(rotki, (address := make_evm_address()))
    for module in LidoCsmStakingModule:
        db.add_node_operator(address=address, node_operator_id=3, staking_module=module)

    def get_stats(
            fetcher: LidoCsmMetricsFetcher,
            node_operator_id: int,
    ) -> LidoCsmNodeOperatorStats:
        return LidoCsmNodeOperatorStats(
            operator_type=LidoCsmOperatorType.PERMISSIONLESS,
            current_bond=FVal(fetcher.staking_module.value),
            required_bond=FVal('2.0'),
            claimable_bond=FVal('0.5'),
            total_deposited_validators=node_operator_id,
            rewards_steth=FVal('0.3'),
        )

    with patch(
        'rotkehlchen.api.rest.LidoCsmMetricsFetcher.get_operator_stats',
        autospec=True,
        side_effect=get_stats,
    ):
        result = assert_proper_sync_response_with_result(
            requests.post(api_url_for(rotkehlchen_api_server, 'lidocsmmetricsresource')),
        )

    assert {
        (entry['staking_module_id'], entry['metrics']['bond']['current'])
        for entry in result
    } == {(module.value, str(module.value)) for module in LidoCsmStakingModule}
    persisted = set()
    for entry in db.get_node_operators():
        assert entry.metrics is not None
        persisted.add((entry.staking_module, entry.metrics.current_bond))
    assert persisted == {(module, FVal(module.value)) for module in LidoCsmStakingModule}


def test_add_lido_csm_node_operator_rejects_unsupported_staking_module(
        rotkehlchen_api_server: APIServer,
) -> None:
    _register_eth_account(
        rotki=rotkehlchen_api_server.rest_api.rotkehlchen,
        address=(address := make_evm_address()),
    )
    assert_error_response(
        requests.put(
            api_url_for(rotkehlchen_api_server, 'lidocsmnodeoperatorresource'),
            json={'address': address, 'node_operator_id': 1, 'staking_module_id': 4},
        ),
        status_code=HTTPStatus.BAD_REQUEST,
        contained_in_msg='Must be one of: 3, 5',
    )
