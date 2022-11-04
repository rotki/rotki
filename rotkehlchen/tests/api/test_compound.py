import random
import warnings as test_warnings
from contextlib import ExitStack
from http import HTTPStatus
from typing import Any, Dict

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.compound.compound import A_COMP, CompoundEvent
from rotkehlchen.chain.ethereum.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_CDAI, A_CUSDC, A_DAI, A_ETH, A_USDC
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.serialize import process_result_list
from rotkehlchen.tests.conftest import TestEnvironment, requires_env
from rotkehlchen.tests.utils.api import (
    ASYNC_TASK_WAIT_TIMEOUT,
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import Timestamp

TEST_ACC1 = '0x2bddEd18E2CA464355091266B7616956944ee7eE'


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('ethereum_modules', [['compound']])
def test_query_compound_balances(rotkehlchen_api_server, ethereum_accounts):
    """Check querying the compound balances endpoint works. Uses real data.

    TODO: Here we should use a test account for which we will know what balances
    it has and we never modify
    """
    async_query = random.choice([False, True])
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
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id, timeout=60)
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
        assert A_COMP.identifier in rewards


@pytest.mark.parametrize('ethereum_accounts', [[TEST_ACC1]])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_dsr']])
def test_query_compound_balances_module_not_activated(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=None)

    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "compoundbalancesresource",
        ))
    assert_error_response(
        response=response,
        contained_in_msg='compound module is not activated',
        status_code=HTTPStatus.CONFLICT,
    )


mocked_historical_prices: Dict[str, Any] = {
    A_DAI.identifier: {
        'USD': {
            1581184577: FVal('1.008'),
            1587601131: FVal('1.016'),
            1587766729: FVal('1.016'),
            1582378248: FVal('1.026'),
            1597288823: FVal('1.018'),
            1598038125: FVal('1.006'),
            1597954197: FVal('1.005'),
            1597369409: FVal('1.008'),
            1597452580: FVal('1.011'),
            1598138282: FVal('1.003'),
            1597982781: FVal('1.006'),
        },
    },
    A_CUSDC.identifier: {
        'USD': {
            1588459991: FVal('0.02102'),
            1586159213: FVal('0.02102'),
            1585790265: FVal('0.02101'),
            1585844643: FVal('0.02101'),
            1588464109: FVal('0.02102'),
        },
    },
    A_USDC.identifier: {
        'USD': {
            1585558039: ONE,
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
    A_COMP.identifier: {
        'USD': {
            1597452580: FVal('196.9'),
        },
    },
}
mocked_current_prices: Dict[str, Any] = {}


TEST_ACCOUNTS = [
    # For mint/redeem
    '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
    # For borrowing/liquidations
    '0xC440f3C87DC4B6843CABc413916220D4f4FeD117',
    # For mint/redeem + comp
    '0xF59D4937BF1305856C3a267bB07791507a3377Ee',
    # For repay
    '0x65304d6aff5096472519ca86a6a1fea31cb47Ced',
]


@requires_env([TestEnvironment.NIGHTLY])
@pytest.mark.parametrize('ethereum_accounts', [TEST_ACCOUNTS])
@pytest.mark.parametrize('ethereum_modules', [['compound']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [mocked_historical_prices])
@pytest.mark.parametrize('mocked_current_prices', [mocked_current_prices])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_query_compound_history(rotkehlchen_api_server, ethereum_accounts):  # pylint: disable=unused-argument  # noqa: E501
    """Check querying the compound history endpoint works. Uses real data"""
    expected_events = [CompoundEvent(
        event_type='mint',
        address=string_to_evm_address('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'),
        block_number=9443573,
        timestamp=Timestamp(1581184577),
        asset=A_DAI.resolve_to_crypto_asset(),
        value=Balance(amount=FVal('2988.4343'), usd_value=FVal('3012.3417744')),
        to_asset=A_CDAI.resolve_to_crypto_asset(),
        to_value=Balance(amount=FVal('148015.6966153'), usd_value=FVal('3012.3417744')),
        realized_pnl=None,
        tx_hash='0xacc2e21f911a4e438966694e9ad16747878a15dae52de62a09f1ebabc8b26c8d',
        log_index=130,
    ), CompoundEvent(
        event_type='redeem',
        address=string_to_evm_address('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'),
        block_number=9533397,
        timestamp=Timestamp(1582378248),
        asset=A_CDAI.resolve_to_crypto_asset(),
        value=Balance(amount=FVal('148015.6966153'), usd_value=FVal('3075.319825609865034570156')),
        to_asset=A_DAI.resolve_to_crypto_asset(),
        to_value=Balance(
            amount=FVal('2997.387744259127714006'),
            usd_value=FVal('3075.319825609865034570156'),
        ),
        realized_pnl=Balance(
            amount=FVal('8.953444259127714006'),
            usd_value=FVal('9.186233809865034570156'),
        ),
        tx_hash='0xd88138b22ef340f9ce572408b8cef10ea8df91768aee5205d5edbdb6fca76665',
        log_index=178,
    ), CompoundEvent(
        event_type='redeem',
        address=string_to_evm_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
        block_number=9772026,
        timestamp=Timestamp(1585558039),
        asset=A_CUSDC.resolve_to_crypto_asset(),
        value=Balance(amount=FVal('95.18807265'), usd_value=FVal('2')),
        to_asset=A_USDC.resolve_to_crypto_asset(),
        to_value=Balance(amount=FVal('2'), usd_value=FVal('2')),
        realized_pnl=Balance(amount=FVal('2'), usd_value=FVal('2')),
        tx_hash='0x0e1b732cd29d65be155dba7675379ce5e63e1902773609b3b15b2d685ff6bc3d',
        log_index=80,
    ), CompoundEvent(
        event_type='borrow',
        address=string_to_evm_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
        block_number=9772043,
        timestamp=Timestamp(1585558230),
        asset=A_ETH.resolve_to_crypto_asset(),
        value=Balance(amount=FVal('0.0108'), usd_value=FVal('1.428948')),
        to_asset=None,
        to_value=None,
        realized_pnl=None,
        tx_hash='0x3ddf908ddeba7d95bc4903f5dff9c47a2c79ac517ad3aa4ebf6330ce949e7297',
        log_index=95,
    ), CompoundEvent(
        event_type='borrow',
        address=string_to_evm_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
        block_number=9785337,
        timestamp=Timestamp(1585735112),
        asset=A_ETH.resolve_to_crypto_asset(),
        value=Balance(amount=FVal('0.0001'), usd_value=FVal('0.013605')),
        to_asset=None,
        to_value=None,
        realized_pnl=None,
        tx_hash='0x301527f6f3c728a298f971d68a5bc917c31ad0ce477d91c0daf653b248e9b072',
        log_index=65,
    ), CompoundEvent(
        event_type='liquidation',
        address=string_to_evm_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
        block_number=9789509,
        timestamp=Timestamp(1585790265),
        asset=A_ETH.resolve_to_crypto_asset(),
        value=Balance(
            amount=FVal('0.005450929782112544'),
            usd_value=FVal('0.77179714784931510496'),
        ),
        to_asset=A_CUSDC.resolve_to_crypto_asset(),
        to_value=Balance(amount=FVal('38.40932319'), usd_value=FVal('0.8069798802219')),
        realized_pnl=None,
        tx_hash='0x1b4827a2fd4d6fcbf10bdd1a6c845c1a5f294ca39c60c90610b2a4d9fa5f6a33',
        log_index=15,
    ), CompoundEvent(
        event_type='borrow',
        address=string_to_evm_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
        block_number=9791832,
        timestamp=Timestamp(1585820470),
        asset=A_ETH.resolve_to_crypto_asset(),
        value=Balance(amount=FVal('0.00065'), usd_value=FVal('0.0920335')),
        to_asset=None,
        to_value=None,
        realized_pnl=None,
        tx_hash='0xdc01f2eb8833ac877051900f14b0c5fc99b8b948cb00cfacede84ee8b670a272',
        log_index=26,
    ), CompoundEvent(
        event_type='liquidation',
        address=string_to_evm_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
        block_number=9793584,
        timestamp=Timestamp(1585844643),
        asset=A_ETH.resolve_to_crypto_asset(),
        value=Balance(
            amount=FVal('0.003050579405059551'),
            usd_value=FVal('0.43193153796238182609'),
        ),
        to_asset=A_CUSDC.resolve_to_crypto_asset(),
        to_value=Balance(amount=FVal('22.13273963'), usd_value=FVal('0.4650088596263')),
        realized_pnl=None,
        tx_hash='0x82806e5f41c31a85c89b0ce096d784002d867df9d7f2d67bf07d47407e1a1225',
        log_index=67,
    ), CompoundEvent(
        event_type='borrow',
        address=string_to_evm_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
        block_number=9798001,
        timestamp=Timestamp(1585903297),
        asset=A_ETH.resolve_to_crypto_asset(),
        value=Balance(amount=FVal('0.000326'), usd_value=FVal('0.04611270')),
        to_asset=None,
        to_value=None,
        realized_pnl=None,
        tx_hash='0xf051267460d677f794f0d4a9a39e74b1e76733f0956809d7acee2f339a48e6d9',
        log_index=121,
    ), CompoundEvent(
        event_type='liquidation',
        address=string_to_evm_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
        block_number=9817257,
        timestamp=Timestamp(1586159213),
        asset=A_ETH.resolve_to_crypto_asset(),
        value=Balance(amount=FVal('0.00168867571834735'), usd_value=FVal('0.2898780738115061010')),
        to_asset=A_CUSDC,
        to_value=Balance(amount=FVal('13.06078395'), usd_value=FVal('0.2745376786290')),
        realized_pnl=None,
        tx_hash='0x160c0e6db0df5ea0c1cc9b1b31bd90c842ef793c9b2ab496efdc62bdd80eeb52',
        log_index=35,
    ), CompoundEvent(
        event_type='mint',
        address=string_to_evm_address('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'),
        block_number=9925459,
        timestamp=Timestamp(1587601131),
        asset=A_DAI.resolve_to_crypto_asset(),
        value=Balance(
            amount=FVal('1275.827510923051483475'),
            usd_value=FVal('1296.240751097820307210600'),
        ),
        to_asset=A_CDAI.resolve_to_crypto_asset(),
        to_value=Balance(
            amount=FVal('62413.91974005'),
            usd_value=FVal('1296.240751097820307210600'),
        ),
        realized_pnl=None,
        tx_hash='0xe5f31776ada64cb566c5d8601791aa75a18c72963af29d6646bd6557a4e6a4ae',
        log_index=123,
    ), CompoundEvent(
        event_type='redeem',
        address=string_to_evm_address('0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'),
        block_number=9937855,
        timestamp=Timestamp(1587766729),
        asset=A_CDAI.resolve_to_crypto_asset(),
        value=Balance(
            amount=FVal('62413.91974005'),
            usd_value=FVal('1296.381817566529086447552'),
        ),
        to_asset=A_DAI.resolve_to_crypto_asset(),
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
        address=string_to_evm_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
        block_number=9989623,
        timestamp=Timestamp(1588459991),
        asset=A_ETH.resolve_to_crypto_asset(),
        value=Balance(amount=FVal('0.0005'), usd_value=FVal('0.107075')),
        to_asset=A_CUSDC,
        to_value=Balance(amount=FVal('5.48471654'), usd_value=FVal('0.1152887416708')),
        realized_pnl=None,
        tx_hash='0x02356347600dc86ba35effba30207277b022b05f5573f4dd66ba667c6656b3f3',
        log_index=75,
    ), CompoundEvent(
        event_type='liquidation',
        address=string_to_evm_address('0xC440f3C87DC4B6843CABc413916220D4f4FeD117'),
        block_number=9989922,
        timestamp=Timestamp(1588464109),
        asset=A_ETH.resolve_to_crypto_asset(),
        value=Balance(amount=FVal('0.00053619065955'), usd_value=FVal('0.1126322099450730')),
        to_asset=A_CUSDC.resolve_to_crypto_asset(),
        to_value=Balance(amount=FVal('5.88169987'), usd_value=FVal('0.1236333312674')),
        realized_pnl=None,
        tx_hash='0xaa15bf91ae1db6f981cf72372cbb497bc51cfb750a7e61fdb18719756741c734',
        log_index=70,
    ), CompoundEvent(
        event_type='mint',
        address=string_to_evm_address('0xF59D4937BF1305856C3a267bB07791507a3377Ee'),
        block_number=10649153,
        timestamp=Timestamp(1597288823),
        asset=A_DAI.resolve_to_crypto_asset(),
        value=Balance(
            amount=FVal('738.31900592'),
            usd_value=FVal('751.60874802656'),
        ),
        to_asset=A_CDAI.resolve_to_crypto_asset(),
        to_value=Balance(amount=FVal('35867.06208787'), usd_value=FVal('751.60874802656')),
        realized_pnl=None,
        tx_hash='0x02fcd49e347d72736d97c7fd7b592c74066b278c1e1d921222f1dcf57c6c733b',
        log_index=216,
    ), CompoundEvent(
        event_type='mint',
        address=string_to_evm_address('0xF59D4937BF1305856C3a267bB07791507a3377Ee'),
        block_number=10655225,
        timestamp=Timestamp(1597369409),
        asset=A_DAI.resolve_to_crypto_asset(),
        value=Balance(
            amount=FVal('1155.06093'),
            usd_value=FVal('1164.30141744'),
        ),
        to_asset=A_CDAI.resolve_to_crypto_asset(),
        to_value=Balance(amount=FVal('56104.69550574'), usd_value=FVal('1164.30141744')),
        realized_pnl=None,
        tx_hash='0xd867ff816645d72ce230969eba06c3be262b55a9ddc2a542ddd936f2d95abb42',
        log_index=37,
    ), CompoundEvent(
        event_type='redeem',
        address=string_to_evm_address('0xF59D4937BF1305856C3a267bB07791507a3377Ee'),
        block_number=10661485,
        timestamp=Timestamp(1597452580),
        asset=A_CDAI.resolve_to_crypto_asset(),
        value=Balance(
            amount=FVal('91971.75759361'),
            usd_value=FVal('1914.508668506095318289145'),
        ),
        to_asset=A_DAI.resolve_to_crypto_asset(),
        to_value=Balance(
            amount=FVal('1893.678208215722372195'),
            usd_value=FVal('1914.508668506095318289145'),
        ),
        realized_pnl=Balance(
            amount=FVal('0.298272295722372195'),
            usd_value=FVal('0.301553290975318289145'),
        ),
        tx_hash='0x2bbb296ebf1d94ad28d54c446cb23709b3463c4a43d8b5b8438ff39b2b985e1c',
        log_index=33,
    ), CompoundEvent(
        event_type='comp',
        address=string_to_evm_address('0xF59D4937BF1305856C3a267bB07791507a3377Ee'),
        block_number=10661485,
        timestamp=Timestamp(1597452580),
        asset=A_COMP.resolve_to_crypto_asset(),
        value=Balance(
            amount=FVal('0.002931620367040859'),
            usd_value=FVal('0.5772360502703451371'),
        ),
        to_asset=None,
        to_value=None,
        realized_pnl=Balance(
            amount=FVal('0.002931620367040859'),
            usd_value=FVal('0.5772360502703451371'),
        ),
        tx_hash='0x2bbb296ebf1d94ad28d54c446cb23709b3463c4a43d8b5b8438ff39b2b985e1c',
        log_index=25,
    ), CompoundEvent(
        event_type='mint',
        address=string_to_evm_address('0xF59D4937BF1305856C3a267bB07791507a3377Ee'),
        block_number=10699185,
        timestamp=Timestamp(1597954197),
        asset=A_DAI.resolve_to_crypto_asset(),
        value=Balance(
            amount=FVal('1164.9182'),
            usd_value=FVal('1170.7427910'),
        ),
        to_asset=A_CDAI.resolve_to_crypto_asset(),
        to_value=Balance(amount=FVal('56547.38087342'), usd_value=FVal('1170.7427910')),
        realized_pnl=None,
        tx_hash='0xb79ca0cf277596d707333127bc470d8dc81c796feee480e68f523263605fcd7c',
        log_index=50,
    ), CompoundEvent(
        event_type='redeem',
        address=string_to_evm_address('0xF59D4937BF1305856C3a267bB07791507a3377Ee'),
        block_number=10701348,
        timestamp=Timestamp(1597982781),
        asset=A_CDAI.resolve_to_crypto_asset(),
        value=Balance(
            amount=FVal('56547.38087342'),
            usd_value=FVal('1171.943202171921841981350'),
        ),
        to_asset=A_DAI.resolve_to_crypto_asset(),
        to_value=Balance(
            amount=FVal('1164.953481284216542725'),
            usd_value=FVal('1171.943202171921841981350'),
        ),
        realized_pnl=Balance(
            amount=FVal('0.035281284216542725'),
            usd_value=FVal('0.035492971921841981350'),
        ),
        tx_hash='0xa931709c3f2e6a53c0cfe7e65a9b73d1e6cfe2f6a1dec907578c443d66130cb6',
        log_index=69,
    ), CompoundEvent(
        event_type='mint',
        address=string_to_evm_address('0xF59D4937BF1305856C3a267bB07791507a3377Ee'),
        block_number=10705474,
        timestamp=Timestamp(1598038125),
        asset=A_DAI.resolve_to_crypto_asset(),
        value=Balance(
            amount=FVal('157.51085'),
            usd_value=FVal('158.45591510'),
        ),
        to_asset=A_CDAI.resolve_to_crypto_asset(),
        to_value=Balance(amount=FVal('7645.20779168'), usd_value=FVal('158.45591510')),
        realized_pnl=None,
        tx_hash='0x7c9126e0a13ec76af3f79b431f37deb26acdc9a0e0c7b24e82aae159f50fc8e2',
        log_index=38,
    ), CompoundEvent(
        event_type='redeem',
        address=string_to_evm_address('0xF59D4937BF1305856C3a267bB07791507a3377Ee'),
        block_number=10712981,
        timestamp=Timestamp(1598138282),
        asset=A_CDAI.resolve_to_crypto_asset(),
        value=Balance(
            amount=FVal('7645.20779168'),
            usd_value=FVal('158.000066488385791637265'),
        ),
        to_asset=A_DAI.resolve_to_crypto_asset(),
        to_value=Balance(
            amount=FVal('157.527484036276960755'),
            usd_value=FVal('158.000066488385791637265'),
        ),
        realized_pnl=Balance(
            amount=FVal('0.016634036276960755'),
            usd_value=FVal('0.016683938385791637265'),
        ),
        tx_hash='0x667f4eb9952ffdb5141741fecb8a798f207b02adc480bb8063b055c4b10ad1dd',
        log_index=38,
    )]

    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        eth_balances=['1000000', '2000000', '33000030003', '42323213'],
        token_balances={},
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
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
            # Big timeout since this test can take a long time
            outcome = wait_for_async_task(
                rotkehlchen_api_server,
                task_id,
                timeout=ASYNC_TASK_WAIT_TIMEOUT * 10,
            )
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    assert len(result) == 5
    expected_events = process_result_list(expected_events)
    # Check only 22 first events, since this is how many there were in the time of
    # the writing of the test. Also don't check events for one of the addresses
    # as it's added later, has many events and it's only to see we handle repay correctly
    to_check_events = [
        x for x in result['events'] if x['address'] != '0x65304d6aff5096472519ca86a6a1fea31cb47Ced'
    ]
    assert to_check_events[:22] == expected_events
    # Check one repay event
    other_events = [
        x for x in result['events'] if x['address'] == '0x65304d6aff5096472519ca86a6a1fea31cb47Ced'
    ]
    assert other_events[12]['event_type'] == 'repay'
    expected_hash = '0x48a3e2ef8a746383deac34d74f2f0ea0451b2047701fbed4b9d769a782888eea'
    assert other_events[12]['tx_hash'] == expected_hash
    assert other_events[12]['value']['amount'] == '0.55064402'

    # Check interest profit mappings
    profit_0 = result['interest_profit']['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']
    assert FVal(profit_0[A_DAI.identifier]['amount']) > FVal(9)
    profit_1 = result['interest_profit']['0xC440f3C87DC4B6843CABc413916220D4f4FeD117']
    assert FVal(profit_1[A_USDC.identifier]['amount']) > FVal(2)
    profit_2 = result['interest_profit']['0xF59D4937BF1305856C3a267bB07791507a3377Ee']
    assert FVal(profit_2[A_DAI.identifier]['amount']) > FVal('0.3')

    # Check debt loss mappings
    debt_0 = result['debt_loss']['0xC440f3C87DC4B6843CABc413916220D4f4FeD117']
    assert FVal(debt_0[A_CUSDC.identifier]['amount']) > FVal('84')
    assert FVal(debt_0['ETH']['amount']) > FVal('0.000012422')

    # Check liquidation profit mappings
    lprofit_0 = result['liquidation_profit']['0xC440f3C87DC4B6843CABc413916220D4f4FeD117']
    assert FVal(lprofit_0['ETH']['amount']) > FVal('0.000012')

    # Check rewards mappings
    rewards_0 = result['rewards']['0xC440f3C87DC4B6843CABc413916220D4f4FeD117']
    assert FVal(rewards_0[A_COMP.identifier]['amount']) > FVal('0.000036')
    rewards_1 = result['rewards']['0xF59D4937BF1305856C3a267bB07791507a3377Ee']
    assert FVal(rewards_1[A_COMP.identifier]['amount']) > FVal('0.003613')


@pytest.mark.parametrize('ethereum_modules', [['compound']])
@pytest.mark.parametrize('start_with_valid_premium', [False])
def test_query_compound_history_non_premium(rotkehlchen_api_server, ethereum_accounts):  # pylint: disable=unused-argument  # noqa: E501
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "compoundhistoryresource",
    ))
    assert_error_response(
        response=response,
        contained_in_msg='Currently logged in user testuser does not have a premium subscription',
        status_code=HTTPStatus.CONFLICT,
    )
