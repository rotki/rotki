import random
import warnings as test_warnings
from contextlib import ExitStack
from http import HTTPStatus

import pytest
import requests
from flaky import flaky

from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import EventType
from rotkehlchen.chain.ethereum.manager import NodeName
from rotkehlchen.chain.ethereum.modules.uniswap import (
    UNISWAP_EVENTS_PREFIX,
    UniswapPoolEvent,
    UniswapPoolEventsBalance,
)
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants.assets import A_WETH
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
from rotkehlchen.tests.utils.constants import (
    A_DOLLAR_BASED,
    AVADO_POOL_NODE_NAME,
    BLOCKSOUT_NODE_NAME,
    MYCRYPTO_NODE_NAME,
    TXHASH_HEX_TO_BYTES,
)
from rotkehlchen.tests.utils.ethereum import INFURA_TEST
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import AssetAmount, Price, SupportedBlockchain, Timestamp

# Addresses
# DAI/WETH pool: 0xA478c2975Ab1Ea89e8196811F51A7B7Ade33eB11
# From that pool find a holder and test
LP_HOLDER_ADDRESS = string_to_evm_address('0xc4d15CbE36BE26596fA676Ff1B21421541d7e8e6')
LP_V3_HOLDER_ADDRESS = string_to_evm_address('0xE545F1385740278E54052A53a93C198b05f6F687')

# Uniswap Factory contract
TEST_ADDRESS_FACTORY_CONTRACT = (
    string_to_evm_address('0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f')
)


@pytest.mark.parametrize('ethereum_accounts', [[LP_HOLDER_ADDRESS]])
@pytest.mark.parametrize('ethereum_modules', [['compound']])
def test_get_balances_module_not_activated(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
):
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'uniswapbalancesresource'),
    )
    assert_error_response(
        response=response,
        contained_in_msg='uniswap module is not activated',
        status_code=HTTPStatus.CONFLICT,
    )


UNISWAP_TEST_OPTIONS = [
    # Test with infura (as own node), many open nodes, and premium + graph
    (False, (NodeName(name='own', endpoint=INFURA_TEST, owned=True, blockchain=SupportedBlockchain.ETHEREUM), MYCRYPTO_NODE_NAME)),  # noqa: E501
    (False, (MYCRYPTO_NODE_NAME, BLOCKSOUT_NODE_NAME, AVADO_POOL_NODE_NAME)),
    (True, ()),
]
# Skipped infura and many open nodes for now in the CI. Fails flakily due to timeouts
# from time to time. We should run locally to make sure that it still works.
SKIPPED_UNISWAP_TEST_OPTIONS = [UNISWAP_TEST_OPTIONS[-1]]


@pytest.mark.parametrize('ethereum_accounts', [[LP_HOLDER_ADDRESS]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize(
    'start_with_valid_premium,ethereum_manager_connect_at_start',
    SKIPPED_UNISWAP_TEST_OPTIONS,
)
def test_get_balances(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
        start_with_valid_premium,
):
    """Check querying the uniswap balances endpoint works. Uses real data

    Checks the functionality both for the graph queries (when premium) and simple
    onchain queries (without premium)

    THIS IS SUPER FREAKING SLOW. BE WARNED.
    """
    async_query = random.choice([False, True])
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'uniswapbalancesresource'),
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

    if LP_HOLDER_ADDRESS not in result or len(result[LP_HOLDER_ADDRESS]) == 0:
        test_warnings.warn(
            UserWarning(f'Test account {LP_HOLDER_ADDRESS} has no uniswap balances'),
        )
        return

    address_balances = result[LP_HOLDER_ADDRESS]
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


# Get events history tests

TEST_EVENTS_ADDRESS_1 = '0x6C0F75eb3D69B9Ea2fB88dbC37fc086a12bBC93F'


def get_expected_events_balances_2():
    """Function so no price (unknown) assets can be resolved only when existing in the DB"""
    A_DICE = EvmToken('eip155:1/erc20:0xCF67CEd76E8356366291246A9222169F4dBdBe64')  # noqa: N806
    return [
        # Response index 0
        UniswapPoolEventsBalance(
            address=string_to_evm_address(TEST_EVENTS_ADDRESS_1),
            pool_address=string_to_evm_address("0xC585Cc7b9E77AEa3371764320740C18E9aEC9c55"),
            token0=A_WETH,
            token1=A_DICE,
            events=[
                UniswapPoolEvent(
                    tx_hash=TXHASH_HEX_TO_BYTES['0x1e7fd116b316af49f6c52b3ca44f3c5d24c2a6f80a5b5e674b5f94155bd2cec4'],  # noqa: 501
                    log_index=99,
                    address=string_to_evm_address(TEST_EVENTS_ADDRESS_1),
                    timestamp=Timestamp(1598270334),
                    event_type=EventType.MINT_UNISWAP,
                    pool_address=string_to_evm_address("0xC585Cc7b9E77AEa3371764320740C18E9aEC9c55"),  # noqa: E501
                    token0=A_WETH,
                    token1=A_DICE,
                    amount0=AssetAmount(FVal('1.580431277572006656')),
                    amount1=AssetAmount(FVal('3')),
                    usd_price=Price(FVal('1281.249386421513581165086356450817')),
                    lp_amount=AssetAmount(FVal('2.074549918528068811')),
                ),
                UniswapPoolEvent(
                    tx_hash=TXHASH_HEX_TO_BYTES['0x140bdba831f9494cf0ead6d57009e1eae45ed629a78ee74ccbf49018afae0ffa'],  # noqa: 501
                    log_index=208,
                    address=string_to_evm_address(TEST_EVENTS_ADDRESS_1),
                    timestamp=Timestamp(1599000975),
                    event_type=EventType.BURN_UNISWAP,
                    pool_address=string_to_evm_address("0xC585Cc7b9E77AEa3371764320740C18E9aEC9c55"),  # noqa: E501
                    token0=A_WETH,
                    token1=A_DICE,
                    amount0=AssetAmount(FVal('0.970300671842796406')),
                    amount1=AssetAmount(FVal('4.971799615456732408')),
                    usd_price=Price(FVal('928.8590296681781753390482605315881')),
                    lp_amount=AssetAmount(FVal('2.074549918528068811')),
                ),
            ],
            profit_loss0=AssetAmount(FVal('-0.610130605729210250')),
            profit_loss1=AssetAmount(FVal('1.971799615456732408')),
            usd_profit_loss=Price(FVal('-352.3903567533354058260380955')),
        ),
        # Response index 3
        UniswapPoolEventsBalance(
            address=string_to_evm_address(TEST_EVENTS_ADDRESS_1),
            pool_address=string_to_evm_address("0x7CDc560CC66126a5Eb721e444abC30EB85408f7A"),  # noqa: E501
            token0=EvmToken('eip155:1/erc20:0x26E43759551333e57F073bb0772F50329A957b30'),  # DGVC
            token1=A_WETH,
            events=[
                UniswapPoolEvent(
                    tx_hash=TXHASH_HEX_TO_BYTES['0xc612f05bf9f3d814ffbe3649feacbf5bda213297bf7af53a56956814652fe9cc'],  # noqa: 501
                    log_index=171,
                    address=string_to_evm_address(TEST_EVENTS_ADDRESS_1),
                    timestamp=Timestamp(1598391968),
                    event_type=EventType.MINT_UNISWAP,
                    pool_address=string_to_evm_address("0x7CDc560CC66126a5Eb721e444abC30EB85408f7A"),    # noqa: 501 # noqa: E501
                    token0=EvmToken('eip155:1/erc20:0x26E43759551333e57F073bb0772F50329A957b30'),    # noqa: 501 # DGVC
                    token1=A_WETH,
                    amount0=AssetAmount(FVal('322.230285353834005677')),
                    amount1=AssetAmount(FVal('1.247571217823345601')),
                    usd_price=Price(FVal('945.2160925652988117900888961551871')),
                    lp_amount=AssetAmount(FVal('18.297385821424685079')),
                ),
                UniswapPoolEvent(
                    tx_hash=TXHASH_HEX_TO_BYTES['0x597f8790a3b9353114b364777c9d32373930e5ad6b8c8f97a58cd2dd58f12b89'],  # noqa: 501
                    log_index=201,
                    address=string_to_evm_address(TEST_EVENTS_ADDRESS_1),
                    timestamp=Timestamp(1598607431),
                    event_type=EventType.BURN_UNISWAP,
                    pool_address=string_to_evm_address("0x7CDc560CC66126a5Eb721e444abC30EB85408f7A"),  # noqa: E501
                    token0=EvmToken('eip155:1/erc20:0x26E43759551333e57F073bb0772F50329A957b30'),    # noqa: 501 # DGVC
                    token1=A_WETH,
                    amount0=AssetAmount(FVal('224.7799861151427733')),
                    amount1=AssetAmount(FVal('1.854907037058682998')),
                    usd_price=Price(FVal('1443.169924855633931959022716230101')),
                    lp_amount=AssetAmount(FVal('18.297385821424685079')),
                ),
            ],
            profit_loss0=AssetAmount(FVal('-97.450299238691232377')),
            profit_loss1=AssetAmount(FVal('0.607335819235337397')),
            usd_profit_loss=Price(FVal('497.9538322903351201689338200')),
        ),
    ]


@pytest.mark.parametrize('ethereum_accounts', [[TEST_EVENTS_ADDRESS_1]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_events_history_filtering_by_timestamp_case1(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
):
    """Test the events balances from 1604273256 to 1604283808 (both included).

    LPs involved by the address within this time range: 1, $BASED-WETH

    By calling the endpoint with a specific time range:
      - Not all the events are queried.
      - The events balances do not factorise the current balances in the
      protocol (meaning the response amounts should be assertable).
    """
    expected_events_balances_1 = [
        UniswapPoolEventsBalance(
            address=string_to_evm_address(TEST_EVENTS_ADDRESS_1),
            pool_address=string_to_evm_address("0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89"),
            token0=A_DOLLAR_BASED.resolve_to_evm_token(),
            token1=A_WETH.resolve_to_evm_token(),
            events=[
                UniswapPoolEvent(
                    tx_hash=TXHASH_HEX_TO_BYTES['0xa9ce328d0e2d2fa8932890bfd4bc61411abd34a4aaa48fc8b853c873a55ea824'],  # noqa: 501
                    log_index=263,
                    address=string_to_evm_address(TEST_EVENTS_ADDRESS_1),
                    timestamp=Timestamp(1604273256),
                    event_type=EventType.MINT_UNISWAP,
                    pool_address=string_to_evm_address("0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89"),  # noqa: E501
                    token0=A_DOLLAR_BASED.resolve_to_evm_token(),
                    token1=A_WETH.resolve_to_evm_token(),
                    amount0=AssetAmount(FVal('605.773209925184996494')),
                    amount1=AssetAmount(FVal('1.106631443395672732')),
                    usd_price=Price(FVal('872.4689300619698095220125311431804')),
                    lp_amount=AssetAmount(FVal('1.220680531244355402')),
                ),
                UniswapPoolEvent(
                    tx_hash=TXHASH_HEX_TO_BYTES['0x27ddad4f187e965a3ee37257b75d297ff79b2663fd0a2d8d15f7efaccf1238fa'],  # noqa: 501
                    log_index=66,
                    address=string_to_evm_address(TEST_EVENTS_ADDRESS_1),
                    timestamp=Timestamp(1604283808),
                    event_type=EventType.BURN_UNISWAP,
                    pool_address=string_to_evm_address('0x55111baD5bC368A2cb9ecc9FBC923296BeDb3b89'),  # noqa: E501
                    token0=A_DOLLAR_BASED.resolve_to_evm_token(),
                    token1=A_WETH.resolve_to_evm_token(),
                    amount0=AssetAmount(FVal('641.26289347330654345')),
                    amount1=AssetAmount(FVal('1.046665027131675546')),
                    usd_price=Price(FVal('837.2737746532695970921908229899852')),
                    lp_amount=AssetAmount(FVal('1.220680531244355402')),
                ),
            ],
            profit_loss0=AssetAmount(FVal('35.489683548121546956')),
            profit_loss1=AssetAmount(FVal('-0.059966416263997186')),
            usd_profit_loss=Price(FVal('-35.19515540870021242982170811')),
        ),
    ]

    # Call time range
    from_timestamp = 1604273256
    to_timestamp = 1604283808

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
            name=f'{UNISWAP_EVENTS_PREFIX}_{TEST_EVENTS_ADDRESS_1}',
            start_ts=Timestamp(0),
            end_ts=from_timestamp,
        )
        with ExitStack() as stack:
            # patch ethereum/etherscan to not autodetect tokens
            setup.enter_ethereum_patches(stack)
            response = requests.get(
                api_url_for(
                    rotkehlchen_api_server,
                    'uniswapeventshistoryresource',
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
        assert expected_events_balances_1[0].serialize() == events_balances[0]

        # Make sure they end up in the DB
        events = rotki.data.db.get_amm_events(cursor, [EventType.MINT_UNISWAP, EventType.BURN_UNISWAP])  # noqa: E501
        assert len(events) != 0
        # test uniswap data purging from the db works
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            'namedethereummoduledataresource',
            module_name='uniswap',
        ))
        assert_simple_ok_response(response)
        events = rotki.data.db.get_amm_events(cursor, [EventType.MINT_UNISWAP, EventType.BURN_UNISWAP])  # noqa: E501
        assert len(events) == 0


@pytest.mark.parametrize('ethereum_accounts', [[TEST_EVENTS_ADDRESS_1]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_events_history_filtering_by_timestamp_case2(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
):
    """Test the events balances from 1598270334 to 1599000975 (both included).

    LPs involved by the address within this time range: 4, only 2 tested.
      - 0: WETH-DICE (tested)
      - 1: DAI-ZOMBIE
      - 2: SHRIMP-WETH
      - 3: DGVC-WETH (tested)

    By calling the endpoint with a specific time range:
      - Not all the events are queried.
      - The events balances do not factorise the current balances in the
      protocol (meaning the response amounts should be assertable).
    """
    # Call time range
    from_timestamp = 1598270334
    to_timestamp = 1599000975

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
            name=f'{UNISWAP_EVENTS_PREFIX}_{TEST_EVENTS_ADDRESS_1}',
            start_ts=Timestamp(0),
            end_ts=from_timestamp,
        )
        with ExitStack() as stack:
            # patch ethereum/etherscan to not autodetect tokens
            setup.enter_ethereum_patches(stack)
            response = requests.get(
                api_url_for(
                    rotkehlchen_api_server,
                    'uniswapeventshistoryresource',
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

        assert len(events_balances) == 4
        expected_events_balances_2 = get_expected_events_balances_2()
        assert expected_events_balances_2[0].serialize() == events_balances[0]
        assert expected_events_balances_2[1].serialize() == events_balances[3]

        # Make sure they end up in the DB
        events = rotki.data.db.get_amm_events(cursor, [EventType.MINT_UNISWAP, EventType.BURN_UNISWAP])  # noqa: E501
        assert len(events) != 0
        # test all data purging from the db works and also deletes uniswap data
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            'ethereummoduledataresource',
        ))
        assert_simple_ok_response(response)
        events = rotki.data.db.get_amm_events(cursor, [EventType.MINT_UNISWAP, EventType.BURN_UNISWAP])  # noqa: E501
        assert len(events) == 0


PNL_TEST_ACC = '0x1F9fbD2F6a8754Cd56D4F56ED35338A63C5Bfd1f'


@pytest.mark.parametrize('ethereum_accounts', [[PNL_TEST_ACC]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_events_pnl(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
):
    """Test the uniswap events history profit and loss calculation"""
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
    json_data = {
        'async_query': async_query,
        'from_timestamp': 0,
        'to_timestamp': 1609282296,  # time until which pnl was checked
    }
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server, 'uniswapeventshistoryresource'),
            json=json_data,
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=120)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    events_balances = result[PNL_TEST_ACC]
    assert len(events_balances) == 3
    # Assert some event details
    assert events_balances[0]['events'][0]['amount0'] == '42.247740079122297434'
    assert events_balances[0]['events'][0]['amount1'] == '0.453409755976350622'
    assert events_balances[0]['events'][0]['event_type'] == 'mint'
    assert events_balances[0]['events'][1]['amount0'] == '64.052160560025177012'
    assert events_balances[0]['events'][1]['amount1'] == '0.455952395125600548'
    assert events_balances[0]['events'][1]['event_type'] == 'burn'
    # Most importantly assert the profit loss
    assert FVal(events_balances[0]['profit_loss0']) >= FVal('21.8')
    assert FVal(events_balances[0]['profit_loss1']) >= FVal('0.00254')
    assert FVal(events_balances[1]['profit_loss0']) >= FVal('-0.0013')
    assert FVal(events_balances[1]['profit_loss1']) >= FVal('0.054')
    assert FVal(events_balances[2]['profit_loss0']) >= FVal('50.684')
    assert FVal(events_balances[2]['profit_loss1']) >= FVal('-0.04')


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ADDRESS_FACTORY_CONTRACT]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_events_history_get_all_events_empty(
        rotkehlchen_api_server,
        ethereum_accounts,  # pylint: disable=unused-argument
):
    """Test get all the events balances for an address without events.
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
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server, 'uniswapeventshistoryresource'),
            json={'async_query': async_query},
        )
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=120)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    assert result == {}


@flaky(max_runs=3, min_passes=1)  # etherscan may occasionally time out
@pytest.mark.parametrize('ethereum_accounts', [[LP_V3_HOLDER_ADDRESS]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_v3_balances_premium(rotkehlchen_api_server):
    """Check querying the uniswap balances v3 endpoint works."""
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'uniswapv3balancesresource'),
    )
    result = assert_proper_response_with_result(response)

    if LP_V3_HOLDER_ADDRESS not in result or len(result[LP_V3_HOLDER_ADDRESS]) == 0:
        test_warnings.warn(
            UserWarning(f'Test account {LP_V3_HOLDER_ADDRESS} has no uniswap balances'),
        )
        return

    address_balances = result[LP_V3_HOLDER_ADDRESS]
    for lp in address_balances:
        # LiquidityPool attributes
        assert lp['address'].startswith('0x')
        assert len(lp['price_range']) == 2
        assert isinstance(lp['price_range'], list)
        assert lp['nft_id']
        assert isinstance(lp['nft_id'], str)
        assert len(lp['assets']) == 2
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
            assert lp_asset['total_amount'] is not None
            assert lp_asset['usd_price']
            assert len(lp_asset['user_balance']) == 2
            assert lp_asset['user_balance']['amount']
            assert lp_asset['user_balance']['usd_value']


@pytest.mark.parametrize('ethereum_accounts', [[LP_V3_HOLDER_ADDRESS]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [False])
def test_get_v3_balances_no_premium(rotkehlchen_api_server):
    """Check querying the uniswap balances v3 endpoint works."""
    response = requests.get(
        api_url_for(rotkehlchen_api_server, 'uniswapv3balancesresource'),
    )
    result = assert_proper_response_with_result(response)

    if LP_V3_HOLDER_ADDRESS not in result or len(result[LP_V3_HOLDER_ADDRESS]) == 0:
        test_warnings.warn(
            UserWarning(f'Test account {LP_V3_HOLDER_ADDRESS} has no uniswap balances'),
        )
        return

    address_balances = result[LP_V3_HOLDER_ADDRESS]
    for lp in address_balances:
        # LiquidityPool attributes
        assert lp['address'].startswith('0x')
        assert len(lp['price_range']) == 2
        assert isinstance(lp['price_range'], list)
        assert lp['nft_id']
        assert isinstance(lp['nft_id'], str)
        assert len(lp['assets']) == 2
        assert lp['user_balance']['amount']
        assert lp['user_balance']['usd_value']

        # LiquidityPoolAsset attributes
        for lp_asset in lp['assets']:
            lp_asset_type = type(lp_asset['asset'])

            assert lp_asset_type in (str, dict)

            # Unknown asset, at least contains token address
            if lp_asset_type is dict:
                assert lp_asset['asset']['ethereum_address'].startswith('0x')
            # Known asset, contains identifier
            else:
                assert not lp_asset['asset'].startswith('0x')
            # check that the user_balances are not returned
            assert lp_asset['total_amount'] is None
            assert FVal(lp_asset['usd_price']) == ZERO
            assert FVal(lp_asset['user_balance']['amount']) == ZERO
            assert FVal(lp_asset['user_balance']['usd_value']) == ZERO
