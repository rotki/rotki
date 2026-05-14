from collections.abc import Sequence
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from rotkehlchen.assets.asset import SolanaToken
from rotkehlchen.chain.solana.modules.jupiter.balances import (
    JUPITER_LEND_EVENT_TYPES,
    JupiterLendBalances,
)
from rotkehlchen.chain.solana.modules.jupiter.constants import CPT_JUPITER
from rotkehlchen.constants import ZERO
from rotkehlchen.db.filtering import SolanaEventFilterQuery
from rotkehlchen.errors.misc import NotSPLConformant
from rotkehlchen.externalapis.jupiter import JupiterPosition, JupiterPositionReserve
from rotkehlchen.fval import FVal
from rotkehlchen.types import SolanaAddress, TokenKind

if TYPE_CHECKING:
    from rotkehlchen.chain.solana.node_inquirer import SolanaInquirer
    from rotkehlchen.db.dbhandler import DBHandler
    from rotkehlchen.externalapis.jupiter import Jupiter

OWNER: SolanaAddress = SolanaAddress('FPjx1P5RUwKGESWoksupbNexMiCzwsYhazoN268kpBvt')
USDC_SOLANA: SolanaAddress = SolanaAddress('EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v')
JUPUSD_SOLANA: SolanaAddress = SolanaAddress('JuprjznTrTSp2UFa3ZBUFgwdAmtZCq4MQCwysN55USD')


@pytest.fixture(name='jupiter_api')
def fixture_jupiter_api(database: 'DBHandler') -> 'Jupiter':
    from rotkehlchen.externalapis.jupiter import Jupiter
    return Jupiter(database=database)


@pytest.fixture(name='jupiter_lend_balances')
def fixture_jupiter_lend_balances(
        database: 'DBHandler',
        solana_inquirer: 'SolanaInquirer',
        jupiter_api: 'Jupiter',
) -> JupiterLendBalances:
    return JupiterLendBalances(
        database=database,
        solana_inquirer=solana_inquirer,
        jupiter=jupiter_api,
    )


def _token(address: SolanaAddress, decimals: int) -> SolanaToken:
    return SolanaToken.initialize(
        address=address,
        token_kind=TokenKind.SPL_TOKEN,
        decimals=decimals,
    )


def _positions(reserves: Sequence[tuple[SolanaAddress, FVal, FVal]]) -> list[JupiterPosition]:
    return [JupiterPosition(
        owner=OWNER,
        reserves=[
            JupiterPositionReserve(
                token=token,
                collateral_amount=collateral,
                debt_amount=debt,
            ) for token, collateral, debt in reserves
        ],
    )]


def test_jupiter_lend_balance_addresses_are_narrowed_by_lend_event_types(
        jupiter_lend_balances: JupiterLendBalances,
) -> None:
    with patch.object(
        SolanaEventFilterQuery,
        'make',
        wraps=SolanaEventFilterQuery.make,
    ) as filter_make:
        assert jupiter_lend_balances.addresses_with_jupiter_events([OWNER]) == []

    filter_make.assert_called_once()
    assert filter_make.call_args.kwargs['counterparties'] == [CPT_JUPITER]
    assert filter_make.call_args.kwargs['type_and_subtype_combinations'] == JUPITER_LEND_EVENT_TYPES  # noqa: E501


def test_jupiter_lend_balances_return_empty_without_jupiter_events(
        jupiter_lend_balances: JupiterLendBalances,
) -> None:
    with patch.object(jupiter_lend_balances.jupiter, 'get_positions') as get_positions:
        assert jupiter_lend_balances.query_balances([OWNER]) == {}

    get_positions.assert_not_called()


def test_jupiter_lend_balances_return_empty_without_positions(
        jupiter_lend_balances: JupiterLendBalances,
) -> None:
    with (
        patch.object(
            jupiter_lend_balances,
            'addresses_with_jupiter_events',
            return_value=[OWNER],
        ),
        patch.object(jupiter_lend_balances.jupiter, 'get_positions', return_value=[]),
    ):
        assert jupiter_lend_balances.query_balances([OWNER]) == {}


@pytest.mark.vcr(filter_headers=['x-api-key'])
def test_jupiter_lend_balances_include_collateral_and_debt(
        jupiter_lend_balances: JupiterLendBalances,
) -> None:
    usdc_token = _token(USDC_SOLANA, 6)
    jupusd_token = _token(JUPUSD_SOLANA, 6)

    def get_token(address: SolanaAddress, **kwargs) -> SolanaToken:
        if address == USDC_SOLANA:
            return usdc_token
        if address == JUPUSD_SOLANA:
            return jupusd_token
        raise NotSPLConformant('Only USDC and JupUSD are relevant for this test')

    with (
        patch.object(
            jupiter_lend_balances,
            'addresses_with_jupiter_events',
            return_value=[OWNER],
        ),
        patch.object(jupiter_lend_balances.jupiter, '_get_api_key', return_value=None),
        patch(
            'rotkehlchen.chain.solana.modules.jupiter.balances.get_or_create_solana_token',
            side_effect=get_token,
        ),
        patch(
            'rotkehlchen.inquirer.Inquirer.find_main_currency_prices',
            return_value={usdc_token: FVal('1'), jupusd_token: FVal('1')},
        ),
    ):
        result = jupiter_lend_balances.query_balances([OWNER])

    assert result[OWNER].assets[jupusd_token][CPT_JUPITER].amount == FVal('6004.070026')
    assert result[OWNER].assets[jupusd_token][CPT_JUPITER].value == FVal('6004.070026')
    assert result[OWNER].liabilities[usdc_token][CPT_JUPITER].amount == FVal('1219809.898632')
    assert result[OWNER].liabilities[usdc_token][CPT_JUPITER].value == FVal('1219809.898632')


def test_jupiter_lend_balances_keep_amounts_without_price(
        jupiter_lend_balances: JupiterLendBalances,
) -> None:
    usdc_token = _token(USDC_SOLANA, 6)

    with (
        patch.object(
            jupiter_lend_balances,
            'addresses_with_jupiter_events',
            return_value=[OWNER],
        ),
        patch.object(jupiter_lend_balances.jupiter, 'get_positions', return_value=_positions([
            (USDC_SOLANA, FVal('500'), FVal(0)),
        ])),
        patch(
            'rotkehlchen.chain.solana.modules.jupiter.balances.get_or_create_solana_token',
            return_value=usdc_token,
        ),
        patch('rotkehlchen.inquirer.Inquirer.find_main_currency_prices', return_value={}),
    ):
        result = jupiter_lend_balances.query_balances([OWNER])

    assert result[OWNER].assets[usdc_token][CPT_JUPITER].amount == FVal('500')
    assert result[OWNER].assets[usdc_token][CPT_JUPITER].value == ZERO
