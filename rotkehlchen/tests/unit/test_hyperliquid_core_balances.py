from collections import defaultdict
from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.utils import get_or_create_evm_token
from rotkehlchen.chain.evm.types import NodeName, WeightedNode, string_to_evm_address
from rotkehlchen.chain.hyperliquid.manager import HyperliquidManager
from rotkehlchen.constants import DEFAULT_BALANCE_LABEL
from rotkehlchen.constants.assets import A_HYPE, A_USDC
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.externalapis.hyperliquid import HyperliquidAPI
from rotkehlchen.fval import FVal
from rotkehlchen.types import ChainID, SupportedBlockchain

ADDR_A = string_to_evm_address('0x7fC1b7863251Ac7F83c7a4E83ccd00d129Ee844c')
REPORTED_STHYPE_HOLDER = string_to_evm_address('0xD2D4867b8886C0cfC3DE5CcD5203EC66C6183764')
STHYPE_ADDRESS = string_to_evm_address('0xfFaa4a3D97fE9107Cef8a3F48c069F577Ff76cC1')
WSTHYPE_ADDRESS = string_to_evm_address('0x94e8396e0869c9F2200760aF0621aFd240E1CF38')
A_STHYPE = Asset('eip155:999/erc20:0xfFaa4a3D97fE9107Cef8a3F48c069F577Ff76cC1')
A_WSTHYPE = Asset('eip155:999/erc20:0x94e8396e0869c9F2200760aF0621aFd240E1CF38')


def test_query_balances_merges_evm_and_core_balances(
        hyperliquid_manager: HyperliquidManager,
) -> None:
    evm_balances: defaultdict[str, BalanceSheet] = defaultdict(BalanceSheet)
    evm_balances[ADDR_A].assets[A_HYPE][DEFAULT_BALANCE_LABEL] = Balance(
        amount=FVal('0.075'),
        value=FVal('1.5'),
    )

    with (
        patch(
            'rotkehlchen.chain.evm.manager.EvmManager.query_balances',
            return_value=evm_balances,
        ),
        patch('rotkehlchen.chain.hyperliquid.manager.HyperliquidAPI') as mock_api_cls,
        patch('rotkehlchen.chain.hyperliquid.manager.Inquirer') as mock_inquirer,
        patch('rotkehlchen.chain.hyperliquid.manager.CachedSettings'),
    ):
        mock_api_cls.return_value.query_balances.return_value = {A_USDC: FVal('500')}
        mock_inquirer.find_price.return_value = ONE

        result = hyperliquid_manager.query_balances(addresses=[ADDR_A])

    assert result[ADDR_A].assets[A_HYPE][DEFAULT_BALANCE_LABEL].amount == FVal('0.075')
    assert result[ADDR_A].assets[A_USDC][DEFAULT_BALANCE_LABEL].amount == FVal('500')


@pytest.mark.vcr(match_on=['uri', 'method', 'body'], record_mode='once')
@pytest.mark.parametrize('hyperliquid_manager_connect_at_start', [(WeightedNode(
    node_info=NodeName(
        name='hyperliquid',
        endpoint='https://rpc.hyperliquid.xyz/evm',
        owned=False,
        blockchain=SupportedBlockchain.HYPERLIQUID,
    ),
    active=True,
    weight=ONE,
),)])
def test_query_balances_does_not_duplicate_reported_sthype_balance(
        hyperliquid_manager: HyperliquidManager,
        hyperliquid_manager_connect_at_start,
        inquirer,
        database,
) -> None:
    """Regression test for the reported Valantis wstHYPE/stHYPE double counting.

    The reported account has both wstHYPE and stHYPE interfaces detected on HyperEVM.
    They represent the same Valantis staked HYPE position and must not be shown as two
    independent balances.
    """
    sthype = get_or_create_evm_token(
        userdb=database,
        evm_address=STHYPE_ADDRESS,
        chain_id=ChainID.HYPERLIQUID,
        symbol='stHYPE',
        name='Staked HYPE',
        decimals=18,
    )
    wsthype = get_or_create_evm_token(
        userdb=database,
        evm_address=WSTHYPE_ADDRESS,
        chain_id=ChainID.HYPERLIQUID,
        symbol='wstHYPE',
        name='Staked HYPE Shares',
        decimals=18,
    )
    with database.user_write() as write_cursor:
        database.save_tokens_for_address(
            write_cursor=write_cursor,
            address=REPORTED_STHYPE_HOLDER,
            blockchain=SupportedBlockchain.HYPERLIQUID,
            tokens=[sthype, wsthype],
        )

    result = hyperliquid_manager.query_balances(addresses=[REPORTED_STHYPE_HOLDER])
    assets = result[REPORTED_STHYPE_HOLDER].assets
    wsthype_balance = assets[A_WSTHYPE][DEFAULT_BALANCE_LABEL].amount
    assert wsthype_balance == FVal('0.000305155263028739')
    assert A_STHYPE not in assets


def test_query_balances_core_failure_returns_evm_only(
        hyperliquid_manager: HyperliquidManager,
) -> None:
    evm_balances: defaultdict[str, BalanceSheet] = defaultdict(BalanceSheet)
    evm_balances[ADDR_A].assets[A_HYPE][DEFAULT_BALANCE_LABEL] = Balance(
        amount=ONE,
        value=FVal('20'),
    )

    with (
        patch(
            'rotkehlchen.chain.evm.manager.EvmManager.query_balances',
            return_value=evm_balances,
        ),
        patch('rotkehlchen.chain.hyperliquid.manager.HyperliquidAPI') as mock_api_cls,
    ):
        mock_api_cls.return_value.query_balances.side_effect = RemoteError('api down')
        result = hyperliquid_manager.query_balances(addresses=[ADDR_A])

    assert result[ADDR_A].assets[A_HYPE][DEFAULT_BALANCE_LABEL].amount == ONE
    assert len(result[ADDR_A].assets) == 1


def test_query_balances_does_not_double_count_open_perp_margin(globaldb) -> None:
    """Regression test for the reported HYPE/USDC perp double count.

    Hyperliquid reports the USDC margin used by an open perp as held spot USDC and
    in the perp account value. Rotki should replace the duplicated margin with perp
    equity, not add both on top of each other.
    """
    api = HyperliquidAPI()
    with patch.object(api, '_query', side_effect=[
        {
            'balances': [{
                'coin': 'USDC',
                'token': 0,
                'total': '31.79386159',
                'hold': '1.22538',
                'entryNtl': '0.0',
            }],
        }, {
            'marginSummary': {
                'accountValue': '1.20604',
                'totalNtlPos': '12.2476',
                'totalRawUsd': '-11.04156',
                'totalMarginUsed': '1.22476',
            },
            'crossMarginSummary': {
                'accountValue': '1.20604',
                'totalNtlPos': '12.2476',
                'totalRawUsd': '-11.04156',
                'totalMarginUsed': '1.22476',
            },
            'assetPositions': [{
                'type': 'oneWay',
                'position': {
                    'coin': 'HYPE',
                    'szi': '0.2',
                    'positionValue': '12.2476',
                    'unrealizedPnl': '-0.0204',
                    'marginUsed': '1.22476',
                },
            }],
        },
    ]):
        result = api.query_balances(
            address=string_to_evm_address('0x48Bf3df773B557e8068Dd3FC76E13301b8a0De22'),
            include_discovered_dexs=False,
        )

    double_counted_balance = FVal('31.79386159') + FVal('1.20604')
    assert result[api.arb_usdc] == double_counted_balance - FVal('1.22476')


@pytest.mark.vcr(match_on=['uri', 'method', 'body'], record_mode='once')
def test_query_balances_fetches_core_balances_with_vcr(
        globaldb,
) -> None:
    result = HyperliquidAPI().query_balances(
        address=ADDR_A,
        include_discovered_dexs=False,
    )

    assert any(amount > ZERO for amount in result.values())
