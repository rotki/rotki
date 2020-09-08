import random
import warnings as test_warnings
from contextlib import ExitStack
from typing import Any, Dict

import pytest
import requests

from rotkehlchen.accounting.structures import Balance
from rotkehlchen.chain.ethereum.compound import CompoundEvent
from rotkehlchen.constants.assets import A_DAI, A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.deserialize import deserialize_ethereum_address
from rotkehlchen.serialization.serialize import process_result_list
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.constants import A_CDAI, A_CUSDC, A_USDC
from rotkehlchen.tests.utils.rotkehlchen import setup_balances

TEST_ACC1 = '0x65304d6aff5096472519ca86a6a1fea31cb47Ced'


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('ethereum_modules', [['compound']])
@pytest.mark.parametrize('async_query', [True, False])
def test_query_compound_balances(rotkehlchen_api_server, ethereum_accounts, async_query):
    """Check querying the compound balances endpoint works. Uses real data.

    TODO: Here we should use a test account for which we will know what balances
    it has and we never modify
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion'],
    )
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "compoundbalancesresource",
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    if len(result) != 1:
        test_warnings.warn(UserWarning(f'Test account {TEST_ACC1} has no compound balances'))
        return

    lending = result[TEST_ACC1]['lending']
    for _, entry in lending.items():
        assert len(entry) == 2
        assert len(entry['balance']) == 2
        assert 'amount' in entry['balance']
        assert 'usd_value' in entry['balance']
        assert '%' in entry['apy']
    borrowing = result[TEST_ACC1]['borrowing']
    for _, entry in borrowing.items():
        assert len(entry) == 2
        assert len(entry['balance']) == 2
        assert 'amount' in entry['balance']
        assert 'usd_value' in entry['balance']
        assert '%' in entry['apy']
    rewards = result[TEST_ACC1]['rewards']
    if len(rewards) != 0:
        assert len(rewards) == 1
        assert 'COMP' in rewards


mocked_historical_prices: Dict[str, Any] = {
    'DAI': {
        'USD': {
            1581184577: FVal('1.008'),
            1587601131: FVal('1.016'),
            1587766729: FVal('1.016'),
            1582378248: FVal('1.026'),
        },
    },
    'cUSDC': {
        'USD': {
            1588459991: FVal('0.02102'),
            1586159213: FVal('0.02102'),
            1585790265: FVal('0.02101'),
            1585844643: FVal('0.02101'),
            1588464109: FVal('0.02102'),
        },
    },
    'USDC': {
        'USD': {
            1585558039: FVal(1),
        },
    },
    'ETH': {
        'USD': {
            1585735112: FVal('136.05'),
            1585558230: FVal('132.31'),
            1585790265: FVal('141.59'),
            1585820470: FVal('141.59'),
            1585844643: FVal('141.59'),
            1585903297: FVal('141.45'),
            1586159213: FVal('171.66'),
            1588459991: FVal('214.15'),
            1588464109: FVal('210.06'),
        },
    },
}
mocked_current_prices: Dict[str, Any] = {}



TEST_ACCOUNTS = [
    # For mint/redeem
    # '0xCa248E880Da1b0D24fe71D338c4ed04f1faF3b9E',
    '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
    # For borrowing/liquidations
    '0xC440f3C87DC4B6843CABc413916220D4f4FeD117',
]



EXPECTED_EVENTS = [CompoundEvent(
    event_type='mint',
    address=deserialize_ethereum_address('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'),
    block_number=9443573,
    timestamp=1581184577,
    asset=A_DAI,
    value=Balance(amount=FVal('2988.4343'), usd_value=FVal('3012.3417744')),
    to_asset=A_CDAI,
    to_value=Balance(amount=FVal('148015.6966153'), usd_value=FVal('3012.3417744')),
    realized_pnl=None,
    tx_hash='0xacc2e21f911a4e438966694e9ad16747878a15dae52de62a09f1ebabc8b26c8d',
    log_index=130,
), CompoundEvent(
    event_type='redeem',
    address=deserialize_ethereum_address('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'),
    block_number=9533397,
    timestamp=1582378248,
    asset=A_CDAI,
    value=Balance(amount=FVal('148015.6966153'), usd_value=FVal('3075.319825609865034570156')),
    to_asset=A_DAI,
    to_value=Balance(
        amount=FVal('2997.387744259127714006'),
        usd_value=FVal('3075.319825609865034570156'),
    ),
    realized_pnl=Balance(
        amount=FVal('8.953444259127714006'),
        usd_value=FVal('62.978051209865034570156'),
    ),
    tx_hash='0xd88138b22ef340f9ce572408b8cef10ea8df91768aee5205d5edbdb6fca76665',
    log_index=178,
), CompoundEvent(
    event_type='redeem',
    address=deserialize_ethereum_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
    block_number=9772026,
    timestamp=1585558039,
    asset=A_CUSDC,
    value=Balance(amount=FVal('95.18807265'), usd_value=FVal('2')),
    to_asset=A_USDC,
    to_value=Balance(amount=FVal('2'), usd_value=FVal('2')),
    realized_pnl=Balance(amount=FVal('2'), usd_value=FVal('2')),
    tx_hash='0x0e1b732cd29d65be155dba7675379ce5e63e1902773609b3b15b2d685ff6bc3d',
    log_index=80,
), CompoundEvent(
    event_type='borrow',
    address=deserialize_ethereum_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
    block_number=9772043,
    timestamp=1585558230,
    asset=A_ETH,
    value=Balance(amount=FVal('0.0108'), usd_value=FVal('1.428948')),
    to_asset=None,
    to_value=None,
    realized_pnl=None,
    tx_hash='0x3ddf908ddeba7d95bc4903f5dff9c47a2c79ac517ad3aa4ebf6330ce949e7297',
    log_index=95,
), CompoundEvent(
    event_type='borrow',
    address=deserialize_ethereum_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
    block_number=9785337,
    timestamp=1585735112,
    asset=A_ETH,
    value=Balance(amount=FVal('0.0001'), usd_value=FVal('0.013605')),
    to_asset=None,
    to_value=None,
    realized_pnl=None,
    tx_hash='0x301527f6f3c728a298f971d68a5bc917c31ad0ce477d91c0daf653b248e9b072',
    log_index=65,
), CompoundEvent(
    event_type='liquidation',
    address=deserialize_ethereum_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
    block_number=9789509,
    timestamp=1585790265,
    asset=A_ETH,
    value=Balance(amount=FVal('0.005450929782112544'), usd_value=FVal('0.77179714784931510496')),
    to_asset=A_CUSDC,
    to_value=Balance(amount=FVal('38.40932319'), usd_value=FVal('0.8069798802219')),
    realized_pnl=None,
    tx_hash='0x1b4827a2fd4d6fcbf10bdd1a6c845c1a5f294ca39c60c90610b2a4d9fa5f6a33',
    log_index=15,
), CompoundEvent(
    event_type='borrow',
    address=deserialize_ethereum_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
    block_number=9791832,
    timestamp=1585820470,
    asset=A_ETH,
    value=Balance(amount=FVal('0.00065'), usd_value=FVal('0.0920335')),
    to_asset=None,
    to_value=None,
    realized_pnl=None,
    tx_hash='0xdc01f2eb8833ac877051900f14b0c5fc99b8b948cb00cfacede84ee8b670a272',
    log_index=26,
), CompoundEvent(
    event_type='liquidation',
    address=deserialize_ethereum_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
    block_number=9793584,
    timestamp=1585844643,
    asset=A_ETH,
    value=Balance(amount=FVal('0.003050579405059551'), usd_value=FVal('0.43193153796238182609')),
    to_asset=A_CUSDC,
    to_value=Balance(amount=FVal('22.13273963'), usd_value=FVal('0.4650088596263')),
    realized_pnl=None,
    tx_hash='0x82806e5f41c31a85c89b0ce096d784002d867df9d7f2d67bf07d47407e1a1225',
    log_index=67,
), CompoundEvent(
    event_type='borrow',
    address=deserialize_ethereum_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
    block_number=9798001,
    timestamp=1585903297,
    asset=A_ETH,
    value=Balance(amount=FVal('0.000326'), usd_value=FVal('0.04611270')),
    to_asset=None,
    to_value=None,
    realized_pnl=None,
    tx_hash='0xf051267460d677f794f0d4a9a39e74b1e76733f0956809d7acee2f339a48e6d9',
    log_index=121,
), CompoundEvent(
    event_type='liquidation',
    address=deserialize_ethereum_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
    block_number=9817257,
    timestamp=1586159213,
    asset=A_ETH,
    value=Balance(amount=FVal('0.00168867571834735'), usd_value=FVal('0.2898780738115061010')),
    to_asset=A_CUSDC,
    to_value=Balance(amount=FVal('13.06078395'), usd_value=FVal('0.2745376786290')),
    realized_pnl=None,
    tx_hash='0x160c0e6db0df5ea0c1cc9b1b31bd90c842ef793c9b2ab496efdc62bdd80eeb52',
    log_index=35,
), CompoundEvent(
    event_type='mint',
    address=deserialize_ethereum_address('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'),
    block_number=9925459,
    timestamp=1587601131,
    asset=A_DAI,
    value=Balance(
        amount=FVal('1275.827510923051483475'),
        usd_value=FVal('1296.240751097820307210600'),
    ),
    to_asset=A_CDAI,
    to_value=Balance(amount=FVal('62413.91974005'), usd_value=FVal('1296.240751097820307210600')),
    realized_pnl=None,
    tx_hash='0xe5f31776ada64cb566c5d8601791aa75a18c72963af29d6646bd6557a4e6a4ae',
    log_index=123,
), CompoundEvent(
    event_type='redeem',
    address=deserialize_ethereum_address('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'),
    block_number=9937855,
    timestamp=1587766729,
    asset=A_CDAI,
    value=Balance(
        amount=FVal('62413.91974005'),
        usd_value=FVal('1296.381817566529086447552'),
    ),
    to_asset=A_DAI,
    to_value=Balance(
        amount=FVal('1275.966355872567998472'),
        usd_value=FVal('1296.381817566529086447552'),
    ),
    realized_pnl=Balance(
        amount=FVal('0.138844949516514997'),
        usd_value=FVal('0.141066468708779236952'),
    ),
    tx_hash='0x63ec8370b29e3ddad6d59f09a161023b5bc0524eb5ca6c4473a5242f40e2129f',
    log_index=115,
), CompoundEvent(
    event_type='liquidation',
    address=deserialize_ethereum_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
    block_number=9989623,
    timestamp=1588459991,
    asset=A_ETH,
    value=Balance(amount=FVal('0.0005'), usd_value=FVal('0.107075')),
    to_asset=A_CUSDC,
    to_value=Balance(amount=FVal('5.48471654'), usd_value=FVal('0.1152887416708')),
    realized_pnl=None,
    tx_hash='0x02356347600dc86ba35effba30207277b022b05f5573f4dd66ba667c6656b3f3',
    log_index=75,
), CompoundEvent(
    event_type='liquidation',
    address=deserialize_ethereum_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
    block_number=9989922,
    timestamp=1588464109,
    asset=A_ETH,
    value=Balance(amount=FVal('0.00053619065955'), usd_value=FVal('0.1126322099450730')),
    to_asset=A_CUSDC,
    to_value=Balance(amount=FVal('5.88169987'), usd_value=FVal('0.1236333312674')),
    realized_pnl=None,
    tx_hash='0xaa15bf91ae1db6f981cf72372cbb497bc51cfb750a7e61fdb18719756741c734',
    log_index=70,
)]


@pytest.mark.parametrize('ethereum_accounts', [TEST_ACCOUNTS])
@pytest.mark.parametrize('ethereum_modules', [['compound']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [mocked_historical_prices])
@pytest.mark.parametrize('mocked_current_prices', [mocked_current_prices])
@pytest.mark.parametrize('default_mock_price_value', [FVal(1)])
def test_query_compound_history(rotkehlchen_api_server, ethereum_accounts):  # pylint: disable=unused-argument  # noqa: E501
    """Check querying the compound histoy endpoint works. Uses real data"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion'],
    )
    # Since this test can be a bit slow we don't run both async and sync in the same test run
    # Instead we randomly choose one. Eventually both cases will be covered.
    async_query = random.choice([True, False])

    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "compoundhistoryresource",
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            # Timeout of 120 since this test can take a long time
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=120)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    assert len(result) == 4
    expected_events = process_result_list(EXPECTED_EVENTS)
    # Check only 14 first events
    assert result['events'][:14] == expected_events
