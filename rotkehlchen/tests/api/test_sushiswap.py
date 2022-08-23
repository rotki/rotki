import random
import warnings as test_warnings
from contextlib import ExitStack
from http import HTTPStatus

import pytest
import requests

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import EventType
from rotkehlchen.chain.ethereum.modules.sushiswap import (
    SUSHISWAP_EVENTS_PREFIX,
    SushiswapPoolEvent,
    SushiswapPoolEventsBalance,
)
from rotkehlchen.chain.ethereum.trades import AMMSwap, AMMTrade
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.api import (
    ASYNC_TASK_WAIT_TIMEOUT,
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import (
    AssetAmount,
    Location,
    Price,
    Timestamp,
    TradeType,
    deserialize_evm_tx_hash,
)

SWAP_ADDRESS = string_to_evm_address('0x63BC843b9640c4D79d6aE0105bc39F773172d121')


@pytest.mark.parametrize('ethereum_accounts', [[SWAP_ADDRESS]])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('ethereum_modules', [['compound']])
def test_get_balances_module_not_activated(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
):
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'sushiswapbalancesresource'),
    )
    assert_error_response(
        response=response,
        contained_in_msg='sushiswap module is not activated',
        status_code=HTTPStatus.CONFLICT,
    )


@pytest.mark.parametrize('ethereum_accounts', [[SWAP_ADDRESS]])
@pytest.mark.parametrize('ethereum_modules', [['sushiswap']])
@pytest.mark.parametrize(
    'start_with_valid_premium',
    (True,),
)
def test_get_balances(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
        start_with_valid_premium,
):
    """Check querying the sushiswap balances endpoint works. Uses real data

    Checks the functionality both for the graph queries (when premium) and simple
    onchain queries (without premium)
    """
    async_query = random.choice([False, True])
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'sushiswapbalancesresource'),
        json={'async_query': async_query},
    )
    if async_query:
        task_id = assert_ok_async_response(response)
        outcome = wait_for_async_task(
            server=rotkehlchen_api_server,
            task_id=task_id,
            timeout=ASYNC_TASK_WAIT_TIMEOUT * 10,
        )
        assert outcome['message'] == ''
        result = outcome['result']
    else:
        result = assert_proper_response_with_result(response)

    if SWAP_ADDRESS not in result or len(result[SWAP_ADDRESS]) == 0:
        test_warnings.warn(
            UserWarning(f'Test account {SWAP_ADDRESS} has no sushiswap balances'),
        )
        return

    address_balances = result[SWAP_ADDRESS]
    for lp in address_balances:
        # LiquidityPool attributes
        assert lp['address'].startswith('0x')
        assert len(lp['assets']) == 2
        if start_with_valid_premium:
            assert lp['total_supply'] is not None
        else:
            assert lp['total_supply'] is None
        assert lp['user_balance']['amount']
        assert lp['user_balance']['usd_value']

        # LiquidityPoolAsset attributes
        for lp_asset in lp['assets']:
            lp_asset_type = type(lp_asset['asset'])

            assert lp_asset_type in (str, dict)

            # Unknown asset, at least contains token address
            if lp_asset_type is dict:
                assert lp_asset['asset']['evm_address'].startswith('0x')
            # Known asset, contains identifier
            else:
                assert not lp_asset['asset'].startswith('0x')

            if start_with_valid_premium:
                assert lp_asset['total_amount'] is not None
            else:
                assert lp_asset['total_amount'] is None
            assert lp_asset['usd_price']
            assert len(lp_asset['user_balance']) == 2
            assert lp_asset['user_balance']['amount']
            assert lp_asset['user_balance']['usd_value']


def get_expected_trades():
    """Function so no price (unknown) assets can be resolved only when existing in the DB"""
    address = string_to_evm_address('0x63BC843b9640c4D79d6aE0105bc39F773172d121')
    return [AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=EvmToken('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'),
        quote_asset=EvmToken('eip155:1/erc20:0x4b4D2e899658FB59b1D518b68fe836B100ee8958'),
        amount=AssetAmount(FVal('796.857811')),
        rate=Price(FVal('0.0008323741932057006980885326353')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash=deserialize_evm_tx_hash(
                '0x962d904d75c751fbff316f7a2ed280bd93241d5088d747a4f26fe7437813512f',
            ),
            log_index=141,
            address=address,
            from_address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            to_address=string_to_evm_address('0x63BC843b9640c4D79d6aE0105bc39F773172d121'),
            timestamp=Timestamp(1609308616),
            location=Location.SUSHISWAP,
            token0=EvmToken('eip155:1/erc20:0x4b4D2e899658FB59b1D518b68fe836B100ee8958'),
            token1=EvmToken('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'),
            amount0_in=AssetAmount(FVal('0.663283877530785731')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('796.857811')),
        )],
    ), AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=EvmToken('eip155:1/erc20:0x368B3a58B5f49392e5C9E4C998cb0bB966752E51'),
        quote_asset=EvmToken('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
        amount=AssetAmount(FVal('2.223721994593087248')),
        rate=Price(FVal('1124.241252314216598775470692')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash=deserialize_evm_tx_hash(
                '0x90f68af0ebbbb8d4938a4fbd07a70862e806124abd907d1225f25a10afda0180',
            ),
            log_index=26,
            address=address,
            from_address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            to_address=string_to_evm_address('0x06da0fd433C1A5d7a4faa01111c044910A184553'),
            timestamp=Timestamp(1609303966),
            location=Location.SUSHISWAP,
            token0=EvmToken('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            token1=EvmToken('eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
            amount0_in=AssetAmount(FVal('2500')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('3.410623314913014194')),
        ), AMMSwap(
            tx_hash=deserialize_evm_tx_hash(
                '0x90f68af0ebbbb8d4938a4fbd07a70862e806124abd907d1225f25a10afda0180',
            ),
            log_index=29,
            address=address,
            from_address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            to_address=string_to_evm_address('0xC9cB53B48A2f3A9e75982685644c1870F1405CCb'),
            timestamp=Timestamp(1609303966),
            location=Location.SUSHISWAP,
            token0=EvmToken('eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
            token1=EvmToken('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'),
            amount0_in=AssetAmount(FVal('3.410623314913014194')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('2474.601464')),
        ), AMMSwap(
            tx_hash=deserialize_evm_tx_hash(
                '0x90f68af0ebbbb8d4938a4fbd07a70862e806124abd907d1225f25a10afda0180',
            ),
            log_index=32,
            address=address,
            from_address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            to_address=string_to_evm_address('0x63BC843b9640c4D79d6aE0105bc39F773172d121'),
            timestamp=Timestamp(1609303966),
            location=Location.SUSHISWAP,
            token0=EvmToken('eip155:1/erc20:0x368B3a58B5f49392e5C9E4C998cb0bB966752E51'),
            token1=EvmToken('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'),
            amount0_in=AssetAmount(ZERO),
            amount1_in=AssetAmount(FVal('2474.601464')),
            amount0_out=AssetAmount(FVal('2.223721994593087248')),
            amount1_out=AssetAmount(ZERO),
        )],
    ), AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=EvmToken('eip155:1/erc20:0x368B3a58B5f49392e5C9E4C998cb0bB966752E51'),
        quote_asset=EvmToken('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
        amount=AssetAmount(FVal('1.925851508322134245')),
        rate=Price(FVal('1012.539124420295894184748806')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash=deserialize_evm_tx_hash(
                '0xa54bf4c68d435e3c8f432fd7e62b7f8aca497a831a3d3fca305a954484ddd7b2',
            ),
            log_index=205,
            address=address,
            from_address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            to_address=string_to_evm_address('0x06da0fd433C1A5d7a4faa01111c044910A184553'),
            timestamp=Timestamp(1609301469),
            location=Location.SUSHISWAP,
            token0=EvmToken('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            token1=EvmToken('eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
            amount0_in=AssetAmount(FVal('1950')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('2.6455727132446468')),
        ), AMMSwap(
            tx_hash=deserialize_evm_tx_hash(
                '0xa54bf4c68d435e3c8f432fd7e62b7f8aca497a831a3d3fca305a954484ddd7b2',
            ),
            log_index=208,
            address=address,
            from_address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            to_address=string_to_evm_address('0xC9cB53B48A2f3A9e75982685644c1870F1405CCb'),
            timestamp=Timestamp(1609301469),
            location=Location.SUSHISWAP,
            token0=EvmToken('eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
            token1=EvmToken('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'),
            amount0_in=AssetAmount(FVal('2.6455727132446468')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('1936.810111')),
        ), AMMSwap(
            tx_hash=deserialize_evm_tx_hash(
                '0xa54bf4c68d435e3c8f432fd7e62b7f8aca497a831a3d3fca305a954484ddd7b2',
            ),
            log_index=211,
            address=address,
            from_address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            to_address=string_to_evm_address('0x63BC843b9640c4D79d6aE0105bc39F773172d121'),
            timestamp=Timestamp(1609301469),
            location=Location.SUSHISWAP,
            token0=EvmToken('eip155:1/erc20:0x368B3a58B5f49392e5C9E4C998cb0bB966752E51'),
            token1=EvmToken('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'),
            amount0_in=AssetAmount(ZERO),
            amount1_in=AssetAmount(FVal('1936.810111')),
            amount0_out=AssetAmount(FVal('1.925851508322134245')),
            amount1_out=AssetAmount(ZERO),
        )],
    ), AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=EvmToken('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'),
        quote_asset=EvmToken('eip155:1/erc20:0x368B3a58B5f49392e5C9E4C998cb0bB966752E51'),
        amount=AssetAmount(FVal('951.611472')),
        rate=Price(FVal('0.001050849038104071952592013309')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash=deserialize_evm_tx_hash(
                '0xb3cea8179e8bc349661f265937187403ae4914c108d118889d026bac1fbec4e9',
            ),
            log_index=9,
            address=address,
            from_address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            to_address=string_to_evm_address('0x63BC843b9640c4D79d6aE0105bc39F773172d121'),
            timestamp=Timestamp(1609296759),
            location=Location.SUSHISWAP,
            token0=EvmToken('eip155:1/erc20:0x368B3a58B5f49392e5C9E4C998cb0bB966752E51'),
            token1=EvmToken('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'),
            amount0_in=AssetAmount(FVal('1')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('951.611472')),
        )],
    ), AMMTrade(
        trade_type=TradeType.BUY,
        base_asset=EvmToken('eip155:1/erc20:0x368B3a58B5f49392e5C9E4C998cb0bB966752E51'),
        quote_asset=EvmToken('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
        amount=AssetAmount(FVal('1')),
        rate=Price(FVal('511.20342')),
        trade_index=0,
        swaps=[AMMSwap(
            tx_hash=deserialize_evm_tx_hash(
                '0x0ccec8fd15c8d3ab923ee4a2406778f22769e74da20b19a35e614bfead6bab8d',
            ),
            log_index=242,
            address=address,
            from_address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            to_address=string_to_evm_address('0x06da0fd433C1A5d7a4faa01111c044910A184553'),
            timestamp=Timestamp(1609294923),
            location=Location.SUSHISWAP,
            token0=EvmToken('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
            token1=EvmToken('eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
            amount0_in=AssetAmount(FVal('511.20342')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('0.690577933591789501')),
        ), AMMSwap(
            tx_hash=deserialize_evm_tx_hash(
                '0x0ccec8fd15c8d3ab923ee4a2406778f22769e74da20b19a35e614bfead6bab8d',
            ),
            log_index=245,
            address=address,
            from_address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            to_address=string_to_evm_address('0xC9cB53B48A2f3A9e75982685644c1870F1405CCb'),
            timestamp=Timestamp(1609294923),
            location=Location.SUSHISWAP,
            token0=EvmToken('eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
            token1=EvmToken('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'),
            amount0_in=AssetAmount(FVal('0.690577933591789501')),
            amount1_in=AssetAmount(ZERO),
            amount0_out=AssetAmount(ZERO),
            amount1_out=AssetAmount(FVal('506.399839')),
        ), AMMSwap(
            tx_hash=deserialize_evm_tx_hash(
                '0x0ccec8fd15c8d3ab923ee4a2406778f22769e74da20b19a35e614bfead6bab8d',
            ),
            log_index=248,
            address=address,
            from_address=string_to_evm_address('0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F'),
            to_address=string_to_evm_address('0x63BC843b9640c4D79d6aE0105bc39F773172d121'),
            timestamp=Timestamp(1609294923),
            location=Location.SUSHISWAP,
            token0=EvmToken('eip155:1/erc20:0x368B3a58B5f49392e5C9E4C998cb0bB966752E51'),
            token1=EvmToken('eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7'),
            amount0_in=AssetAmount(ZERO),
            amount1_in=AssetAmount(FVal('506.399839')),
            amount0_out=AssetAmount(FVal('1')),
            amount1_out=AssetAmount(ZERO),
        )],
    )]


def _query_and_assert_simple_sushiswap_trades(setup, api_server, async_query):
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            api_server,
            'sushiswaptradeshistoryresource',
        ), json={'async_query': async_query, 'to_timestamp': 1609308616})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(api_server, task_id, timeout=120)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    expected_trades = get_expected_trades()
    for idx, trade in enumerate(result[SWAP_ADDRESS]):
        if idx == len(expected_trades):
            break  # test up to last expected_trades trades from 1609308616
        assert trade == expected_trades[idx].serialize()


@pytest.mark.parametrize('ethereum_accounts', [[SWAP_ADDRESS]])
@pytest.mark.parametrize('ethereum_modules', [['sushiswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_sushiswap_trades_history(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
):
    """Test that the last 11/23 sushiswap trades of the account since 1605437542
    are parsed and returned correctly

    Also test that data are written in the DB and properly retrieved afterwards
    """
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        eth_balances=['33000030003'],
        token_balances={},
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )
    _query_and_assert_simple_sushiswap_trades(setup, rotkehlchen_api_server, async_query)
    # make sure data are written in the DB
    with rotki.data.db.conn.read_ctx() as cursor:
        db_trades = rotki.data.db.get_amm_swaps(cursor)
    assert len(db_trades) == 11
    # Query a 2nd time to make sure that when retrieving from the database everything works fine
    _query_and_assert_simple_sushiswap_trades(setup, rotkehlchen_api_server, async_query)


# Get events history tests
TEST_EVENTS_ADDRESS_1 = '0xE11fc0B43ab98Eb91e9836129d1ee7c3Bc95df50'
EXPECTED_EVENTS_BALANCES_1 = [
    SushiswapPoolEventsBalance(
        address=string_to_evm_address(TEST_EVENTS_ADDRESS_1),
        pool_address=string_to_evm_address("0xC3f279090a47e80990Fe3a9c30d24Cb117EF91a8"),
        token0=EvmToken('eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
        token1=EvmToken('eip155:1/erc20:0xdBdb4d16EdA451D0503b854CF79D55697F90c8DF'),
        events=[
            SushiswapPoolEvent(
                tx_hash=deserialize_evm_tx_hash(
                    '0xb226ddb8cbb286a7a998a35263ad258110eed5f923488f03a8d890572cd4608e',
                ),
                log_index=137,
                address=string_to_evm_address(TEST_EVENTS_ADDRESS_1),
                timestamp=Timestamp(1627401170),
                event_type=EventType.MINT_SUSHISWAP,
                pool_address=string_to_evm_address("0xC3f279090a47e80990Fe3a9c30d24Cb117EF91a8"),  # noqa: E501
                token0=EvmToken('eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                token1=EvmToken('eip155:1/erc20:0xdBdb4d16EdA451D0503b854CF79D55697F90c8DF'),
                amount0=AssetAmount(FVal('0.192426688761441618')),
                amount1=AssetAmount(FVal('1.498665931466140813')),
                usd_price=Price(FVal('874.684787927721190125529172850727')),
                lp_amount=AssetAmount(FVal('0.023925092583833892')),
            ),
        ],
        profit_loss0=AssetAmount(FVal('-0.192426688761441618')),
        profit_loss1=AssetAmount(FVal('-1.498665931466140813')),
        usd_profit_loss=Price(FVal('-874.6847879277211901255291729')),
    ),
]


@pytest.mark.parametrize('ethereum_accounts', [[TEST_EVENTS_ADDRESS_1]])
@pytest.mark.parametrize('ethereum_modules', [['sushiswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_events_history_filtering_by_timestamp(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
):
    """Test the events balances from 1627401169 to 1627401170 (both included)."""
    # Call time range
    from_timestamp = 1627401169
    to_timestamp = 1627401170

    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        eth_balances=['33000030003'],
        token_balances={},
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )
    with rotki.data.db.user_write() as cursor:
        # Force insert address' last used query range, for avoiding query all
        rotki.data.db.update_used_query_range(
            write_cursor=cursor,
            name=f'{SUSHISWAP_EVENTS_PREFIX}_{TEST_EVENTS_ADDRESS_1}',
            start_ts=Timestamp(0),
            end_ts=from_timestamp,
        )
        with ExitStack() as stack:
            # patch ethereum/etherscan to not autodetect tokens
            setup.enter_ethereum_patches(stack)
            response = requests.get(
                api_url_for(
                    rotkehlchen_api_server,
                    'sushiswapeventshistoryresource',
                ),
                json={
                    'async_query': async_query,
                    'from_timestamp': from_timestamp,
                    'to_timestamp': to_timestamp,
                },
            )
            if async_query:
                task_id = assert_ok_async_response(response)
                outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=120)
                assert outcome['message'] == ''
                result = outcome['result']
            else:
                result = assert_proper_response_with_result(response)

        events_balances = result[TEST_EVENTS_ADDRESS_1]

        assert len(events_balances) == 1
        assert EXPECTED_EVENTS_BALANCES_1[0].serialize() == events_balances[0]

        # Make sure they end up in the DB
        events = rotki.data.db.get_amm_events(cursor, [EventType.MINT_SUSHISWAP, EventType.BURN_SUSHISWAP])  # noqa: E501
        assert len(events) != 0
        # test sushiswap data purging from the db works
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            'namedethereummoduledataresource',
            module_name='sushiswap',
        ))
        assert_simple_ok_response(response)
        events = rotki.data.db.get_amm_events(cursor, [EventType.MINT_SUSHISWAP, EventType.BURN_SUSHISWAP])  # noqa: E501
        assert len(events) == 0
