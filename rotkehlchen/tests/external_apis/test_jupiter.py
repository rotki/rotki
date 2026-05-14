from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import Mock, patch

import pytest
import requests

from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.jupiter import Jupiter
from rotkehlchen.fval import FVal
from rotkehlchen.types import SolanaAddress

if TYPE_CHECKING:
    from rotkehlchen.db.dbhandler import DBHandler

OWNER: SolanaAddress = SolanaAddress('FPjx1P5RUwKGESWoksupbNexMiCzwsYhazoN268kpBvt')
USDC_SOLANA: SolanaAddress = SolanaAddress('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')
JUPUSD_SOLANA: SolanaAddress = SolanaAddress('JuprjznTrTSp2UFa3ZBUFgwdAmtZCq4MQCwysN55USD')


@pytest.fixture(name='jupiter_api')
def fixture_jupiter_api(database: 'DBHandler') -> Jupiter:
    return Jupiter(database=database)


def test_jupiter_deserializes_borrowlend_positions(jupiter_api: Jupiter) -> None:
    positions = jupiter_api._deserialize_positions(raw_data={
        'owner': OWNER,
        'elements': [{
            'type': 'borrowlend',
            'data': {
                'suppliedAssets': [{
                    'data': {'address': JUPUSD_SOLANA, 'amount': 10},
                }],
                'borrowedAssets': [{
                    'data': {'address': USDC_SOLANA, 'amount': 5},
                }],
            },
        }],
    })

    assert positions == [jupiter_position := positions[0]]
    assert jupiter_position.owner == OWNER
    assert jupiter_position.reserves[0].token == JUPUSD_SOLANA
    assert jupiter_position.reserves[0].collateral_amount == FVal(10)
    assert jupiter_position.reserves[0].debt_amount == FVal(0)
    assert jupiter_position.reserves[1].token == USDC_SOLANA
    assert jupiter_position.reserves[1].collateral_amount == FVal(0)
    assert jupiter_position.reserves[1].debt_amount == FVal(5)


def test_jupiter_skips_malformed_positions(jupiter_api: Jupiter) -> None:
    assert jupiter_api._deserialize_positions(raw_data={'owner': OWNER, 'elements': [
        {'missing_type': True},
    ]}) == []


@pytest.mark.vcr(filter_headers=['x-api-key'])
def test_jupiter_get_positions_queries_api(jupiter_api: Jupiter) -> None:
    with patch.object(jupiter_api, '_get_api_key', return_value=None):
        positions = jupiter_api.get_positions(owner=OWNER)

    assert len(positions) == 15
    usdc_debt = sum(
        reserve.debt_amount
        for position in positions
        for reserve in position.reserves
        if reserve.token == USDC_SOLANA
    )
    jupusd_collateral = sum(
        reserve.collateral_amount
        for position in positions
        for reserve in position.reserves
        if reserve.token == JUPUSD_SOLANA
    )
    assert usdc_debt == FVal('1219809.841195')
    assert jupusd_collateral == FVal('6004.070026')


def test_jupiter_get_positions_handles_unauthorized(jupiter_api: Jupiter) -> None:
    response = Mock(status_code=HTTPStatus.UNAUTHORIZED, text='Unauthorized')

    with (
        patch.object(jupiter_api, '_get_api_key', return_value='invalid_key'),
        patch('requests.get', return_value=response),
        pytest.raises(RemoteError, match='401 Unauthorized'),
    ):
        jupiter_api.get_positions(owner=OWNER)


def test_jupiter_get_positions_handles_server_error(jupiter_api: Jupiter) -> None:
    response = Mock(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, text='Internal server error')

    with (
        patch.object(jupiter_api, '_get_api_key', return_value='test_key'),
        patch('requests.get', return_value=response),
        pytest.raises(RemoteError, match='500'),
    ):
        jupiter_api.get_positions(owner=OWNER)


def test_jupiter_get_positions_handles_network_error(jupiter_api: Jupiter) -> None:
    with (
        patch.object(jupiter_api, '_get_api_key', return_value='test_key'),
        patch('requests.get', side_effect=requests.exceptions.ConnectionError('no route')),
        pytest.raises(RemoteError, match='no route'),
    ):
        jupiter_api.get_positions(owner=OWNER)
