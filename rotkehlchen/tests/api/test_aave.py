import random
import warnings as test_warnings
from contextlib import ExitStack
from http import HTTPStatus
from typing import Any, Dict

import pytest
import requests

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.api.server import APIServer
from rotkehlchen.chain.ethereum.modules.aave.structures import (
    AaveBorrowEvent,
    AaveDepositWithdrawalEvent,
    AaveInterestEvent,
    AaveLiquidationEvent,
    AaveRepayEvent,
)
from rotkehlchen.constants.assets import A_BUSD, A_DAI, A_ETH, A_LINK, A_USDT, A_WBTC
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.serialization.serialize import process_result_list
from rotkehlchen.tests.utils.aave import (
    A_ADAI_V1,
    A_ALINK_V2,
    A_AWBTC_V1,
    AAVE_TEST_ACC_1,
    AAVE_TEST_ACC_2,
    AAVE_TEST_ACC_3,
    aave_mocked_current_prices,
    aave_mocked_historical_prices,
)
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_ok_async_response,
    assert_proper_response_with_result,
    assert_simple_ok_response,
    wait_for_async_task,
)
from rotkehlchen.tests.utils.checks import assert_serialized_lists_equal
from rotkehlchen.tests.utils.constants import A_ADAI
from rotkehlchen.tests.utils.rotkehlchen import BalancesTestSetup, setup_balances
from rotkehlchen.types import Timestamp, deserialize_evm_tx_hash

AAVE_BALANCESV1_TEST_ACC = '0xC2cB1040220768554cf699b0d863A3cd4324ce32'
AAVE_BALANCESV2_TEST_ACC = '0x8Fe178db26ebA2eEdb22575265bf10A63c395a3d'
AAVE_V2_TEST_ACC = '0x008C00c45D461d7E08acBC4755a4A0a3a94115ee'


@pytest.mark.parametrize('ethereum_accounts', [[AAVE_BALANCESV1_TEST_ACC, AAVE_BALANCESV2_TEST_ACC]])  # noqa: E501
@pytest.mark.parametrize('ethereum_modules', [['aave']])
def test_query_aave_balances(rotkehlchen_api_server, ethereum_accounts):
    """Check querying the aave balances endpoint works. Uses real data.

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
            "aavebalancesresource",
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    if len(result) == 0:
        test_warnings.warn(UserWarning(f'Test account {AAVE_BALANCESV1_TEST_ACC} and {AAVE_BALANCESV2_TEST_ACC} have no aave balances'))  # noqa: E501
        return

    def _assert_valid_entries(balances: Dict[str, Any]) -> None:
        lending = v1_balances['lending']
        for _, entry in lending.items():
            assert len(entry) == 2
            assert len(entry['balance']) == 2
            assert 'amount' in entry['balance']
            assert 'usd_value' in entry['balance']
            assert '%' in entry['apy']
        borrowing = balances['borrowing']
        for _, entry in borrowing.items():
            assert len(entry) == 3
            assert len(entry['balance']) == 2
            assert 'amount' in entry['balance']
            assert 'usd_value' in entry['balance']
            assert '%' in entry['variable_apr']
            assert '%' in entry['stable_apr']

    v1_balances = result.get(AAVE_BALANCESV1_TEST_ACC)
    if v1_balances:
        _assert_valid_entries(v1_balances)
    else:
        test_warnings.warn(UserWarning(f'Test account {AAVE_BALANCESV1_TEST_ACC} has no aave v1 balances'))  # noqa: E501

    v2_balances = result.get(AAVE_BALANCESV2_TEST_ACC)
    if v2_balances:
        _assert_valid_entries(v2_balances)
    else:
        test_warnings.warn(UserWarning(f'Test account {AAVE_BALANCESV2_TEST_ACC} has no aave v2 balances'))  # noqa: E501


@pytest.mark.parametrize('ethereum_accounts', [[AAVE_V2_TEST_ACC]])
@pytest.mark.parametrize('ethereum_modules', [['aave']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [aave_mocked_historical_prices])
@pytest.mark.parametrize('mocked_current_prices', [aave_mocked_current_prices])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_query_aave_history_with_borrowing_v2(rotkehlchen_api_server, ethereum_accounts):  # pylint: disable=unused-argument  # noqa: E501
    """Check querying the aave histoy endpoint works. Uses real data."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )
    _query_simple_aave_history_test_v2(setup, rotkehlchen_api_server, False)


@pytest.mark.parametrize('ethereum_accounts', [[AAVE_BALANCESV1_TEST_ACC]])
@pytest.mark.parametrize('ethereum_modules', [['makerdao_dsr']])
def test_query_aave_balances_module_not_activated(
        rotkehlchen_api_server,
        ethereum_accounts,
):
    async_query = random.choice([False, True])
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(rotki, ethereum_accounts=ethereum_accounts, btc_accounts=None)

    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            rotkehlchen_api_server,
            "aavebalancesresource",
        ), json={'async_query': async_query})

        if async_query:
            task_id = assert_ok_async_response(response)
            outcome = wait_for_async_task(rotkehlchen_api_server, task_id)
            assert outcome['result'] is None
            assert outcome['message'] == 'aave module is not activated'
        else:
            assert_error_response(
                response=response,
                contained_in_msg='aave module is not activated',
                status_code=HTTPStatus.CONFLICT,
            )


def _query_simple_aave_history_test(
        setup: BalancesTestSetup,
        server: APIServer,
        async_query: bool,
) -> None:
    expected_aave_deposit_test_events = [
        AaveDepositWithdrawalEvent(
            event_type='deposit',
            asset=A_DAI.resolve_to_crypto_asset(),
            atoken=A_ADAI_V1.resolve_to_evm_token(),
            value=Balance(
                amount=FVal('102.926986169186236436'),
                usd_value=FVal('104.367963975554843746104'),
            ),
            block_number=9963767,
            timestamp=Timestamp(1588114293),
            tx_hash=deserialize_evm_tx_hash(
                '0x8b72307967c4f7a486c1cb1b6ebca5e549de06e02930ece0399e2096f1a132c5',
            ),
            log_index=72,
        ), AaveDepositWithdrawalEvent(
            event_type='deposit',
            asset=A_DAI.resolve_to_crypto_asset(),
            atoken=A_ADAI_V1.resolve_to_evm_token(),
            value=Balance(
                amount=FVal('160'),
                usd_value=FVal('161.440'),
            ),
            block_number=9987395,
            timestamp=Timestamp(1588430911),
            tx_hash=deserialize_evm_tx_hash(
                '0x78ae48d93e0284d1f9a5e1cd4a7e5f2e3daf65ab5dafb0c4bd626aa90e783d60',
            ),
            log_index=146,
        ), AaveInterestEvent(
            event_type='interest',
            asset=A_ADAI.resolve_to_crypto_asset(),
            value=Balance(
                amount=FVal('0.037901731034995483'),
                usd_value=FVal('0.038242846614310442347'),
            ),
            block_number=9987395,
            timestamp=Timestamp(1588430911),
            tx_hash=deserialize_evm_tx_hash(
                '0x78ae48d93e0284d1f9a5e1cd4a7e5f2e3daf65ab5dafb0c4bd626aa90e783d60',
            ),
            log_index=142,
        ), AaveDepositWithdrawalEvent(
            event_type='deposit',
            asset=A_DAI.resolve_to_crypto_asset(),
            atoken=A_ADAI_V1.resolve_to_evm_token(),
            value=Balance(
                amount=FVal('390'),
                usd_value=FVal('393.510'),
            ),
            block_number=9989872,
            timestamp=Timestamp(1588463542),
            tx_hash=deserialize_evm_tx_hash(
                '0xb9999b06b706dcc973bcf381d69f12620f1bef887082bce9679cf256f7e8023c',
            ),
            log_index=157,
        ), AaveInterestEvent(
            event_type='interest',
            asset=A_ADAI.resolve_to_crypto_asset(),
            value=Balance(
                amount=FVal('0.013768655195843925'),
                usd_value=FVal('0.013892573092606520325'),
            ),
            block_number=9989872,
            timestamp=Timestamp(1588463542),
            tx_hash=deserialize_evm_tx_hash(
                '0xb9999b06b706dcc973bcf381d69f12620f1bef887082bce9679cf256f7e8023c',
            ),
            log_index=153,
        ), AaveDepositWithdrawalEvent(
            event_type='deposit',
            asset=A_DAI.resolve_to_crypto_asset(),
            atoken=A_ADAI_V1.resolve_to_evm_token(),
            value=Balance(
                amount=FVal('58.985239852398524415'),
                usd_value=FVal('59.398136531365314085905'),
            ),
            block_number=10041636,
            timestamp=Timestamp(1589155650),
            tx_hash=deserialize_evm_tx_hash(
                '0x28054d29620515337b8ffb2f7f2dda5b2033beae9844b42359893f4f73d855bc',
            ),
            log_index=35,
        ), AaveInterestEvent(
            event_type='interest',
            asset=A_ADAI.resolve_to_crypto_asset(),
            value=Balance(
                amount=FVal('0.598140134217201945'),
                usd_value=FVal('0.602327115156722358615'),
            ),
            block_number=10041636,
            timestamp=Timestamp(1589155650),
            tx_hash=deserialize_evm_tx_hash(
                '0x28054d29620515337b8ffb2f7f2dda5b2033beae9844b42359893f4f73d855bc',
            ),
            log_index=31,
        ), AaveInterestEvent(
            event_type='interest',
            asset=A_ADAI.resolve_to_crypto_asset(),
            value=Balance(
                amount=FVal('1.13704264707898858'),
                usd_value=FVal('1.14045377502022554574'),
            ),
            block_number=10160566,
            timestamp=Timestamp(1590753905),
            tx_hash=deserialize_evm_tx_hash(
                '0x07ac09cc06c7cd74c7312f3a82c9f77d69ba7a89a4a3b7ded33db07e32c3607c',
            ),
            log_index=152,
        ), AaveDepositWithdrawalEvent(
            event_type='deposit',
            asset=A_DAI.resolve_to_crypto_asset(),
            atoken=A_ADAI_V1.resolve_to_evm_token(),
            value=Balance(
                amount=FVal('168.84093462143338681'),
                usd_value=FVal('171.03586677151202083853'),
            ),
            block_number=10266740,
            timestamp=Timestamp(1592175763),
            tx_hash=deserialize_evm_tx_hash(
                '0x90b818ba8d3b55f332b64f3df58bf37f33addcbfc1f27bd1ec6102ae4bf2d871',
            ),
            log_index=82,
        ), AaveInterestEvent(
            event_type='interest',
            asset=A_ADAI.resolve_to_crypto_asset(),
            value=Balance(
                amount=FVal('3.948991286917379003'),
                usd_value=FVal('4.000328173647304930039'),
            ),
            block_number=10266740,
            timestamp=Timestamp(1592175763),
            tx_hash=deserialize_evm_tx_hash(
                '0x90b818ba8d3b55f332b64f3df58bf37f33addcbfc1f27bd1ec6102ae4bf2d871',
            ),
            log_index=78,
        ), AaveDepositWithdrawalEvent(
            event_type='deposit',
            asset=A_DAI.resolve_to_crypto_asset(),
            atoken=A_ADAI_V1.resolve_to_evm_token(),
            value=Balance(
                amount=FVal('1939.840878392183347402'),
                usd_value=FVal('1976.697855081634831002638'),
            ),
            block_number=10440633,
            timestamp=Timestamp(1594502373),
            tx_hash=deserialize_evm_tx_hash(
                '0xc3a8978418afa1a4f139e9314ac787cacfbed79b1daa28e146bb0bf6fdf79a41',
            ),
            log_index=104,
        ), AaveInterestEvent(
            event_type='interest',
            asset=A_ADAI.resolve_to_crypto_asset(),
            value=Balance(
                amount=FVal('27.824509817913242961'),
                usd_value=FVal('28.353175504453594577259'),
            ),
            block_number=10440633,
            timestamp=Timestamp(1594502373),
            tx_hash=deserialize_evm_tx_hash(
                '0xc3a8978418afa1a4f139e9314ac787cacfbed79b1daa28e146bb0bf6fdf79a41',
            ),
            log_index=100,
        ), AaveDepositWithdrawalEvent(
            event_type='deposit',
            asset=A_DAI.resolve_to_crypto_asset(),
            atoken=A_ADAI_V1.resolve_to_evm_token(),
            value=Balance(
                amount=FVal('2507.675873220870275072'),
                usd_value=FVal('2507.675873220870275072'),
            ),
            block_number=10505913,
            timestamp=Timestamp(1595376667),
            tx_hash=deserialize_evm_tx_hash(
                '0x930879d66d13c37edf25cdbb2d2e85b65c3b2a026529ff4085146bb7a5398410',
            ),
            log_index=96,
        ), AaveInterestEvent(
            event_type='interest',
            asset=A_ADAI.resolve_to_crypto_asset(),
            value=Balance(
                amount=FVal('17.91499070977557364'),
                usd_value=FVal('17.91499070977557364'),
            ),
            block_number=10505913,
            timestamp=Timestamp(1595376667),
            tx_hash=deserialize_evm_tx_hash(
                '0x930879d66d13c37edf25cdbb2d2e85b65c3b2a026529ff4085146bb7a5398410',
            ),
            log_index=92,
        ), AaveInterestEvent(
            event_type='interest',
            asset=A_ADAI.resolve_to_crypto_asset(),
            value=Balance(
                amount=FVal('88.663672238882760399'),
                usd_value=FVal('88.663672238882760399'),
            ),
            block_number=10718983,
            timestamp=Timestamp(1598217272),
            tx_hash=deserialize_evm_tx_hash(
                '0x4fed67963375a3f90916f0cf7cb9e4d12644629e36233025b36060494ffba486',
            ),
            log_index=97,
        ), AaveDepositWithdrawalEvent(
            event_type='withdrawal',
            asset=A_DAI.resolve_to_crypto_asset(),
            atoken=A_ADAI_V1.resolve_to_evm_token(),
            value=Balance(
                amount=FVal('7968.408929477087756071'),
                usd_value=FVal('7968.408929477087756071'),
            ),
            block_number=10718983,
            timestamp=Timestamp(1598217272),
            tx_hash=deserialize_evm_tx_hash(
                '0x4fed67963375a3f90916f0cf7cb9e4d12644629e36233025b36060494ffba486',
            ),
            log_index=102,
        ),
    ]

    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            server,
            'aavehistoryresource',
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            # Big timeout since this test can take a long time
            outcome = wait_for_async_task(server, task_id, timeout=600)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    assert len(result) == 1
    assert len(result[AAVE_TEST_ACC_2]) == 4
    events = result[AAVE_TEST_ACC_2]['events']
    total_earned_interest = result[AAVE_TEST_ACC_2]['total_earned_interest']
    total_lost = result[AAVE_TEST_ACC_2]['total_lost']
    total_earned_liquidations = result[AAVE_TEST_ACC_2]['total_earned_liquidations']
    assert len(total_lost) == 0
    assert len(total_earned_liquidations) == 0
    assert len(total_earned_interest) == 1
    assert len(total_earned_interest[A_ADAI_V1.identifier]) == 2
    assert FVal(total_earned_interest[A_ADAI_V1.identifier]['amount']) >= FVal('24.207179802347627414')  # noqa: E501
    assert FVal(total_earned_interest[A_ADAI_V1.identifier]['usd_value']) >= FVal('24.580592532348742989192')  # noqa: E501

    expected_events = process_result_list(expected_aave_deposit_test_events)
    expected_events = expected_events[:7] + expected_events[8:]

    assert_serialized_lists_equal(
        a=events[:len(expected_events)],
        b=expected_events,
        ignore_keys=['log_index', 'block_number'],
    )


def _query_simple_aave_history_test_v2(
        setup: BalancesTestSetup,
        server: APIServer,
        async_query: bool,
) -> None:
    expected_aave_v2_events = [
        AaveDepositWithdrawalEvent(
            event_type='deposit',
            asset=A_LINK.resolve_to_crypto_asset(),
            atoken=A_ALINK_V2.resolve_to_evm_token(),
            value=Balance(
                amount=FVal('12629.998670888732814733'),
                usd_value=FVal('12629.998670888732814733'),
            ),
            block_number=0,
            timestamp=Timestamp(1615333105),
            tx_hash=deserialize_evm_tx_hash(
                '0x75444c0ae48700f388d05ec8380b3922c4daf1e8eef2476001437b68d36f56a1',
            ),
            log_index=216,
        ), AaveBorrowEvent(
            event_type='borrow',
            asset=A_USDT.resolve_to_crypto_asset(),
            value=Balance(
                amount=FVal('100000'),
                usd_value=FVal('100000'),
            ),
            block_number=0,
            timestamp=Timestamp(1615333284),
            tx_hash=deserialize_evm_tx_hash(
                '0x74e8781fd86e81a87a4ba93bc7755d4a94901765cd72399f0372d36e7a26a03a',
            ),
            log_index=352,
            borrow_rate_mode='stable',
            borrow_rate=FVal('0.088712770921360153608109216'),
            accrued_borrow_interest=ZERO,
        ), AaveRepayEvent(
            event_type='repay',
            asset=A_USDT.resolve_to_crypto_asset(),
            value=Balance(
                amount=FVal('100071.409221'),
                usd_value=FVal('100071.409221'),
            ),
            fee=Balance(amount=ZERO, usd_value=ZERO),
            block_number=0,
            timestamp=Timestamp(1615587042),
            tx_hash=deserialize_evm_tx_hash(
                '0x164e3eafef02ac1a956ba3c7d027506d47de36b34daee1e05ca0d178413911c1',
            ),
            log_index=29,
        ), AaveInterestEvent(
            event_type='interest',
            asset=A_ALINK_V2.resolve_to_crypto_asset(),
            value=Balance(
                amount=FVal('0.092486713379308309'),
                usd_value=FVal('0.092486713379308309'),
            ),
            block_number=0,
            timestamp=Timestamp(1615669328),
            tx_hash=deserialize_evm_tx_hash(
                '0xfeee61357d43e79a2beae9edab860c30db9765964be26eff82c6834d4e2c2db7',
            ),
            log_index=133,
        ), AaveDepositWithdrawalEvent(
            event_type='withdrawal',
            asset=A_LINK.resolve_to_crypto_asset(),
            atoken=A_ALINK_V2.resolve_to_evm_token(),
            value=Balance(
                amount=FVal('12630.091157602112123042'),
                usd_value=FVal('12630.091157602112123042'),
            ),
            block_number=0,
            timestamp=Timestamp(1615669328),
            tx_hash=deserialize_evm_tx_hash(
                '0xfeee61357d43e79a2beae9edab860c30db9765964be26eff82c6834d4e2c2db7',
            ),
            log_index=132,
        ),
    ]

    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            server,
            "aavehistoryresource",
        ), json={'async_query': async_query})
        if async_query:
            task_id = assert_ok_async_response(response)
            # Big timeout since this test can take a long time
            outcome = wait_for_async_task(server, task_id, timeout=600)
            assert outcome['message'] == ''
            result = outcome['result']
        else:
            result = assert_proper_response_with_result(response)

    assert len(result) == 1
    assert len(result[AAVE_V2_TEST_ACC]) == 4
    events = result[AAVE_V2_TEST_ACC]['events']
    total_earned_interest = result[AAVE_V2_TEST_ACC]['total_earned_interest']
    total_lost = result[AAVE_V2_TEST_ACC]['total_lost']
    total_earned_liquidations = result[AAVE_V2_TEST_ACC]['total_earned_liquidations']
    assert len(total_lost) == 1
    assert len(total_earned_liquidations) == 0
    assert len(total_earned_interest) == 1
    assert len(total_earned_interest['eip155:1/erc20:0xa06bC25B5805d5F8d82847D191Cb4Af5A3e873E0']) == 2  # noqa: 501
    assert FVal(total_earned_interest['eip155:1/erc20:0xa06bC25B5805d5F8d82847D191Cb4Af5A3e873E0']['amount']) >= FVal('0.09')  # noqa: E501
    assert FVal(total_earned_interest['eip155:1/erc20:0xa06bC25B5805d5F8d82847D191Cb4Af5A3e873E0']['usd_value']) >= FVal('0.09248')  # noqa: E501

    assert_serialized_lists_equal(
        a=events[:len(expected_aave_v2_events)],
        b=process_result_list(expected_aave_v2_events),
        ignore_keys=None,
    )


@pytest.mark.parametrize('ethereum_accounts', [[AAVE_TEST_ACC_2]])
@pytest.mark.parametrize('ethereum_modules', [['aave']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [aave_mocked_historical_prices])
@pytest.mark.parametrize('mocked_current_prices', [aave_mocked_current_prices])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_query_aave_history(rotkehlchen_api_server, ethereum_accounts):  # pylint: disable=unused-argument  # noqa: E501
    """Check querying the aave histoy endpoint works. Uses real data.

    Since this actually queries real blockchain data for aave it is a very slow test
    due to the sheer amount of log queries. We also use graph in 2nd version of test.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )
    # Since this test is slow we don't run both async and sync in the same test run
    # Instead we randomly choose one. Eventually both cases will be covered.
    async_query = random.choice([True, False])

    _query_simple_aave_history_test(setup, rotkehlchen_api_server, async_query)


@pytest.mark.parametrize('ethereum_accounts', [[AAVE_TEST_ACC_2]])
@pytest.mark.parametrize('ethereum_modules', [['aave']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [aave_mocked_historical_prices])
@pytest.mark.parametrize('mocked_current_prices', [aave_mocked_current_prices])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_query_aave_history2(rotkehlchen_api_server, ethereum_accounts):  # pylint: disable=unused-argument  # noqa: E501
    """Check querying the aave histoy endpoint works. Uses real data.

    Since this actually queries real blockchain data for aave it is a very slow test
    due to the sheer amount of log queries. We also use graph in 2nd version of test.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )
    # Since this test is slow we don't run both async and sync in the same test run
    # Instead we randomly choose one. Eventually both cases will be covered.
    async_query = random.choice([True, False])

    _query_simple_aave_history_test(setup, rotkehlchen_api_server, async_query)


def _query_borrowing_aave_history_test(setup: BalancesTestSetup, server: APIServer) -> None:
    expected_aave_liquidation_test_events = [
        AaveDepositWithdrawalEvent(
            event_type='deposit',
            asset=A_WBTC.resolve_to_crypto_asset(),
            atoken=A_AWBTC_V1.resolve_to_evm_token(),
            value=Balance(
                amount=FVal('1.11'),
                usd_value=FVal('1.11'),
            ),
            block_number=0,
            timestamp=Timestamp(1598799955),
            tx_hash=deserialize_evm_tx_hash(
                '0x400b21334279498fc5b7ff469fec0c5e94620001104f18267c796497a7260ada',
            ),
            log_index=1,
        ), AaveBorrowEvent(
            event_type='borrow',
            asset=A_ETH.resolve_to_crypto_asset(),
            value=Balance(
                amount=FVal('18.5'),
                usd_value=FVal('18.5'),
            ),
            block_number=0,
            timestamp=Timestamp(1598800092),
            tx_hash=deserialize_evm_tx_hash(
                '0x819cdd20760ab68bc7bf9343cb2e5552ab512dcf071afe1c3995a07a379f0961',
            ),
            log_index=2,
            borrow_rate_mode='variable',
            borrow_rate=FVal('0.018558721449222331635565398'),
            accrued_borrow_interest=ZERO,
        ), AaveLiquidationEvent(
            event_type='liquidation',
            collateral_asset=A_WBTC.resolve_to_crypto_asset(),
            collateral_balance=Balance(
                amount=FVal('0.41590034'),
                usd_value=FVal('0.41590034'),
            ),
            principal_asset=A_ETH.resolve_to_crypto_asset(),
            principal_balance=Balance(
                amount=FVal('9.251070299427409111'),
                usd_value=FVal('9.251070299427409111'),
            ),
            block_number=0,
            timestamp=Timestamp(1598941756),
            tx_hash=deserialize_evm_tx_hash(
                '0x00eea6359d247c9433d32620358555a0fd3265378ff146b9511b7cff1ecb7829',
            ),
            log_index=8,
        ), AaveRepayEvent(
            event_type='repay',
            asset=A_ETH.resolve_to_crypto_asset(),
            value=Balance(
                amount=FVal('3.665850591343088034'),
                usd_value=FVal('3.665850591343088034'),
            ),
            fee=Balance(amount=ZERO, usd_value=ZERO),
            block_number=0,
            timestamp=Timestamp(1599023196),
            tx_hash=deserialize_evm_tx_hash(
                '0xb30831fcc5f02e551befa6238839354e602b0a351cdf77eb170c29427c326304',
            ),
            log_index=4,
        ), AaveRepayEvent(
            event_type='repay',
            asset=A_ETH.resolve_to_crypto_asset(),
            value=Balance(
                amount=FVal('5.587531295588010728'),
                usd_value=FVal('5.587531295588010728'),
            ),
            fee=Balance(amount=ZERO, usd_value=ZERO),
            block_number=0,
            timestamp=Timestamp(1599401677),
            tx_hash=deserialize_evm_tx_hash(
                '0xefde39a330215fb189b70e9964b4f7d8cd6f1335c5994899dd04de7a1b30b3aa',
            ),
            log_index=4,
        ), AaveInterestEvent(
            event_type='interest',
            asset=A_AWBTC_V1.resolve_to_crypto_asset(),
            value=Balance(
                amount=FVal('0.00000833'),
                usd_value=FVal('0.00000833'),
            ),
            block_number=0,
            timestamp=Timestamp(1599401782),
            tx_hash=deserialize_evm_tx_hash(
                '0x54eee67a3f1e114d102ea76d69298636caf717e19c1b910264d955c4ba942905',
            ),
            log_index=4,
        ), AaveDepositWithdrawalEvent(
            event_type='withdrawal',
            asset=A_WBTC.resolve_to_crypto_asset(),
            atoken=A_AWBTC_V1.resolve_to_evm_token(),
            value=Balance(
                amount=FVal('0.69410968'),
                usd_value=FVal('0.69410968'),
            ),
            block_number=0,
            timestamp=Timestamp(1599401782),
            tx_hash=deserialize_evm_tx_hash(
                '0x54eee67a3f1e114d102ea76d69298636caf717e19c1b910264d955c4ba942905',
            ),
            log_index=3,
        ), AaveDepositWithdrawalEvent(
            event_type='deposit',
            asset=A_WBTC.resolve_to_crypto_asset(),
            atoken=A_AWBTC_V1.resolve_to_evm_token(),
            value=Balance(
                amount=FVal('1.47386645'),
                usd_value=FVal('1.47386645'),
            ),
            block_number=0,
            timestamp=Timestamp(1601394794),
            tx_hash=deserialize_evm_tx_hash(
                '0x70ca1f4a64bd2be9bff8a6d42e333e89f855a9fec2df643b76fe9401c2b1867c',
            ),
            log_index=1,
        ), AaveBorrowEvent(
            event_type='borrow',
            asset=A_BUSD.resolve_to_crypto_asset(),
            value=Balance(
                amount=FVal('5000'),
                usd_value=FVal('5000'),
            ),
            block_number=0,
            timestamp=Timestamp(1601398506),
            tx_hash=deserialize_evm_tx_hash(
                '0xb59ff2759b37da52537f43aaa5cbce3bcab77ef208cba80e22086610323c2a17',
            ),
            log_index=2,
            borrow_rate_mode='variable',
            borrow_rate=FVal('0.048662000571241866099699838'),
            accrued_borrow_interest=ZERO,
        ),
    ]

    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            server,
            "aavehistoryresource",
        ))
        result = assert_proper_response_with_result(response)

    assert len(result) == 1
    assert len(result[AAVE_TEST_ACC_3]) == 4
    events = result[AAVE_TEST_ACC_3]['events']
    total_earned_interest = result[AAVE_TEST_ACC_3]['total_earned_interest']
    total_lost = result[AAVE_TEST_ACC_3]['total_lost']
    total_earned_liquidations = result[AAVE_TEST_ACC_3]['total_earned_liquidations']

    assert len(total_earned_interest) >= 1
    assert len(total_earned_interest[A_AWBTC_V1.identifier]) == 2
    assert FVal(total_earned_interest[A_AWBTC_V1.identifier]['amount']) >= FVal('0.00000833')
    assert FVal(total_earned_interest[A_AWBTC_V1.identifier]['usd_value']) >= ZERO

    assert len(total_earned_liquidations) == 1
    assert len(total_earned_liquidations['ETH']) == 2
    assert FVal(total_earned_liquidations['ETH']['amount']) >= FVal('9.251070299427409111')
    assert FVal(total_earned_liquidations['ETH']['usd_value']) >= ZERO

    assert len(total_lost) == 3
    eth_lost = total_lost['ETH']
    assert len(eth_lost) == 2
    assert FVal(eth_lost['amount']) >= FVal('0.004452186358507873')
    assert FVal(eth_lost['usd_value']) >= ZERO
    busd_lost = total_lost[A_BUSD.identifier]
    assert len(busd_lost) == 2
    assert FVal(busd_lost['amount']) >= FVal('21.605824443625747553')
    assert FVal(busd_lost['usd_value']) >= ZERO
    wbtc_lost = total_lost[A_WBTC.identifier]
    assert len(wbtc_lost) == 2
    assert FVal(wbtc_lost['amount']) >= FVal('0.41590034')  # ouch
    assert FVal(wbtc_lost['usd_value']) >= ZERO

    expected_events = process_result_list(expected_aave_liquidation_test_events)

    assert_serialized_lists_equal(
        a=events[:len(expected_events)],
        b=expected_events,
        ignore_keys=None,
    )


@pytest.mark.parametrize('ethereum_accounts', [[AAVE_TEST_ACC_3]])
@pytest.mark.parametrize('ethereum_modules', [['aave']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [aave_mocked_historical_prices])
@pytest.mark.parametrize('mocked_current_prices', [aave_mocked_current_prices])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_query_aave_history_with_borrowing(rotkehlchen_api_server, ethereum_accounts):  # pylint: disable=unused-argument  # noqa: E501
    """Check querying the aave histoy endpoint works. Uses real data."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )
    _query_borrowing_aave_history_test(setup, rotkehlchen_api_server)
    # Run it 2 times to make sure that data can be queried properly from the DB
    _query_borrowing_aave_history_test(setup, rotkehlchen_api_server)

    # Make sure events end up in the DB
    with rotki.data.db.conn.read_ctx() as cursor:
        assert len(rotki.data.db.get_aave_events(cursor, AAVE_TEST_ACC_3)) != 0
        # test aave data purging from the db works
        response = requests.delete(api_url_for(
            rotkehlchen_api_server,
            'namedethereummoduledataresource',
            module_name='aave',
        ))
        assert_simple_ok_response(response)
        assert len(rotki.data.db.get_aave_events(cursor, AAVE_TEST_ACC_3)) == 0


def _test_for_duplicates_and_negatives(setup: BalancesTestSetup, server: APIServer) -> None:
    with ExitStack() as stack:
        # patch ethereum/etherscan to not autodetect tokens
        setup.enter_ethereum_patches(stack)
        response = requests.get(api_url_for(
            server,
            "aavehistoryresource",
        ))
        result = assert_proper_response_with_result(response)

    assert len(result) == 1
    result = result[AAVE_TEST_ACC_1]
    assert len(result) == 4

    for _, entry in result['total_earned_interest'].items():
        assert FVal(entry['amount']) > ZERO
    for _, entry in result['total_lost'].items():
        assert FVal(entry['amount']) > ZERO
    for _, entry in result['total_earned_liquidations'].items():
        assert FVal(entry['amount']) > ZERO

    events = result['events']
    events_set = set()
    for idx, event in enumerate(events):
        msg = f'event {event} at index {idx} found twice in the returned events'
        event_hash = hash(event['event_type'] + event['tx_hash'] + str(event['log_index']))
        assert event_hash not in events_set, msg
        events_set.add(event_hash)


@pytest.mark.parametrize('ethereum_accounts', [[AAVE_TEST_ACC_1]])
@pytest.mark.parametrize('ethereum_modules', [['aave']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('mocked_price_queries', [aave_mocked_historical_prices])
@pytest.mark.parametrize('mocked_current_prices', [aave_mocked_current_prices])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
def test_query_aave_history_no_duplicates(rotkehlchen_api_server, ethereum_accounts):  # pylint: disable=unused-argument  # noqa: E501
    """Check querying the aave histoy avoids duplicate event data and keeps totals positive"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    setup = setup_balances(
        rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=None,
        original_queries=['zerion', 'logs', 'blocknobytime'],
    )

    _test_for_duplicates_and_negatives(setup, rotkehlchen_api_server)
    # Test that we still don't get duplicates at the 2nd query which hits the DB
    _test_for_duplicates_and_negatives(setup, rotkehlchen_api_server)


@pytest.mark.parametrize('ethereum_modules', [['aave']])
@pytest.mark.parametrize('start_with_valid_premium', [False])
def test_query_aave_history_non_premium(rotkehlchen_api_server, ethereum_accounts):  # pylint: disable=unused-argument  # noqa: E501
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        "aavehistoryresource",
    ))
    assert_error_response(
        response=response,
        contained_in_msg='Currently logged in user testuser does not have a premium subscription',
        status_code=HTTPStatus.CONFLICT,
    )
