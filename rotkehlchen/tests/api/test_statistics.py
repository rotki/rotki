import contextlib
from contextlib import ExitStack
from http import HTTPStatus
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.bitcoin.btc.constants import BTC_EVENT_IDENTIFIER_PREFIX
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.ens.constants import CPT_ENS
from rotkehlchen.constants.assets import A_BTC, A_ETH, A_ETH2, A_EUR, A_SOL, A_USDC
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.evmtx import DBEvmTx
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.solana_event import SolanaEvent
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_sync_response_with_result,
)
from rotkehlchen.tests.utils.balances import get_asset_balance_total
from rotkehlchen.tests.utils.constants import A_RDN
from rotkehlchen.tests.utils.factories import (
    UNIT_BTC_ADDRESS1,
    UNIT_BTC_ADDRESS2,
    make_btc_tx_id,
    make_evm_address,
    make_evm_tx_hash,
    make_solana_address,
    make_solana_signature,
)
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.tests.utils.rotkehlchen import setup_balances
from rotkehlchen.types import (
    AssetAmount,
    BTCAddress,
    ChainID,
    ChecksumEvmAddress,
    EvmTransaction,
    Location,
    SupportedBlockchain,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
def test_query_statistics_netvalue(
        rotkehlchen_api_server_with_exchanges: 'APIServer',
        ethereum_accounts: list[ChecksumEvmAddress],
        btc_accounts: list[BTCAddress],
) -> None:
    """Test that using the statistics netvalue over time endpoint works"""
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0
    setup = setup_balances(rotki, ethereum_accounts, btc_accounts)

    # query balances and save data in DB to have data to test the statistics endpoint
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'allbalancesresource',
            ), json={'save_data': True},
        )
    assert_proper_response(response)

    # and now test that statistics work fine
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'statisticsnetvalueresource',
        ),
    )

    result = assert_proper_sync_response_with_result(response)
    assert len(result) == 2
    assert len(result['times']) == 1
    assert len(result['data']) == 1


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
@pytest.mark.parametrize('start_with_valid_premium', [True, False])
def test_query_statistics_asset_balance(
        rotkehlchen_api_server_with_exchanges: 'APIServer',
        ethereum_accounts: list[ChecksumEvmAddress],
        btc_accounts: list[BTCAddress],
        start_with_valid_premium: bool,
) -> None:
    """Test that using the statistics asset balance over time endpoint works"""
    start_time = ts_now()
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0
    setup = setup_balances(rotki, ethereum_accounts, btc_accounts)

    # query balances and save data in DB to have data to test the statistics endpoint
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'allbalancesresource',
            ), json={'save_data': True},
        )
    assert_proper_response(response)

    # and now test that statistics work fine for ETH, with default time range (0 - now)
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'statisticsassetbalanceresource',
        ),
        json={'asset': 'ETH'},
    )
    if start_with_valid_premium:
        result = assert_proper_sync_response_with_result(response)
        assert len(result) == 1
        entry = result[0]
        assert len(entry) == 4
        assert FVal(entry['amount']) == get_asset_balance_total(A_ETH, setup)
        assert entry['category'] == 'asset'
        assert entry['time'] >= start_time
        assert entry['usd_value'] is not None
    else:
        assert_error_response(
            response=response,
            contained_in_msg='logged in user testuser does not have a premium subscription',
            status_code=HTTPStatus.FORBIDDEN,
        )

    # and now test that statistics work fine for BTC, with given time range
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'statisticsassetbalanceresource',
        ), json={'from_timestamp': 0, 'to_timestamp': start_time + 60000, 'asset': 'BTC'},
    )
    if start_with_valid_premium:
        result = assert_proper_sync_response_with_result(response)
        assert len(result) == 1
        entry = result[0]
        assert len(entry) == 4
        assert FVal(entry['amount']) == get_asset_balance_total(A_BTC, setup)
        assert entry['time'] >= start_time
        assert entry['category'] == 'asset'
        assert entry['usd_value'] is not None
    else:
        assert_error_response(
            response=response,
            contained_in_msg='logged in user testuser does not have a premium subscription',
            status_code=HTTPStatus.FORBIDDEN,
        )

    # finally test that if the time range is not including the saved balances we get nothing back
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'statisticsassetbalanceresource',
        ), json={'from_timestamp': 0, 'to_timestamp': start_time - 1, 'asset': 'BTC'},
    )
    if start_with_valid_premium:
        result = assert_proper_sync_response_with_result(response)
        assert len(result) == 0
    else:
        assert_error_response(
            response=response,
            contained_in_msg='logged in user testuser does not have a premium subscription',
            status_code=HTTPStatus.FORBIDDEN,
        )


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_query_statistics_asset_balance_errors(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that errors at the statistics asset balance over time endpoint are handled properly"""
    start_time = ts_now()

    # Check that no asset given is an error
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'statisticsassetbalanceresource',
        ),
    )
    assert_error_response(
        response=response,
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Check that an invalid asset given is an error
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'statisticsassetbalanceresource',
        ), json={'from_timestamp': 0, 'to_timestamp': start_time, 'asset': 'NOTAREALASSETLOL'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Unknown asset NOTAREALASSETLOL provided',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Check that giving invalid value for from_timestamp is an error
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'statisticsassetbalanceresource',
        ), json={'from_timestamp': 'dsad', 'to_timestamp': start_time, 'asset': 'BTC'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Failed to deserialize a timestamp entry from string dsad',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Check that giving invalid value for to_timestamp is an error
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'statisticsassetbalanceresource',
        ), json={'from_timestamp': 0, 'to_timestamp': 53434.32, 'asset': 'BTC'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='"Failed to deserialize a timestamp entry from string 53434.32',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('number_of_eth_accounts', [2])
@pytest.mark.parametrize('btc_accounts', [[UNIT_BTC_ADDRESS1, UNIT_BTC_ADDRESS2]])
@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
@pytest.mark.parametrize('start_with_valid_premium', [True, False])
@pytest.mark.parametrize('db_settings', [{'treat_eth2_as_eth': True}, {'treat_eth2_as_eth': False}])  # noqa: E501
def test_query_statistics_value_distribution(
        rotkehlchen_api_server_with_exchanges: 'APIServer',
        ethereum_accounts: list[ChecksumEvmAddress],
        btc_accounts: list[BTCAddress],
        start_with_valid_premium: bool,
        db_settings: dict[str, bool],
) -> None:
    """Test that using the statistics value distribution endpoint works"""
    start_time = ts_now()
    # Disable caching of query results
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    rotki.chains_aggregator.cache_ttl_secs = 0
    token_balances = {A_RDN.resolve_to_evm_token(): ['111000', '4000000']}
    setup = setup_balances(
        rotki=rotki,
        ethereum_accounts=ethereum_accounts,
        btc_accounts=btc_accounts,
        token_balances=token_balances,
        manually_tracked_balances=[ManuallyTrackedBalance(
            identifier=-1,
            asset=A_EUR,
            label='My EUR bank',
            amount=FVal('1550'),
            location=Location.BANKS,
            tags=None,
            balance_type=BalanceType.ASSET,
        ), ManuallyTrackedBalance(
            identifier=2,
            asset=A_ETH2,
            label='John Doe',
            amount=FVal('2.6'),
            location=Location.KRAKEN,
            tags=None,
            balance_type=BalanceType.ASSET,
        )],
    )

    # query balances and save data in DB to have data to test the statistics endpoint
    with ExitStack() as stack:
        setup.enter_all_patches(stack)
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server_with_exchanges,
                'allbalancesresource',
            ), json={'save_data': True},
        )
    assert_proper_response(response)

    def assert_okay_by_location(response: requests.Response) -> None:
        """Helper function to run next query and its assertion twice"""
        if start_with_valid_premium:
            result = assert_proper_sync_response_with_result(response)
            assert len(result) == 6
            locations = {'poloniex', 'binance', 'banks', 'blockchain', 'total', 'kraken'}
            for entry in result:
                assert len(entry) == 3
                assert entry['time'] >= start_time
                assert entry['usd_value'] is not None
                assert entry['location'] in locations
                locations.remove(entry['location'])
            assert len(locations) == 0
        else:
            assert_error_response(
                response=response,
                contained_in_msg='logged in user testuser does not have a premium subscription',
                status_code=HTTPStatus.FORBIDDEN,
            )

    # and now test that statistics work fine for distribution by location for json body
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'statisticsvaluedistributionresource',
        ), json={'distribution_by': 'location'},
    )
    assert_okay_by_location(response)
    # and now test that statistics work fine for distribution by location for query params
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'statisticsvaluedistributionresource',
        ) + '?distribution_by=location',
    )
    assert_okay_by_location(response)

    # finally test that statistics work fine for distribution by asset
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'statisticsvaluedistributionresource',
        ), json={'distribution_by': 'asset'},
    )
    if start_with_valid_premium:
        result = assert_proper_sync_response_with_result(response)
        if db_settings['treat_eth2_as_eth'] is True:
            assert len(result) == 4
            totals = {
                'ETH': get_asset_balance_total(A_ETH, setup) + get_asset_balance_total(A_ETH2, setup),  # noqa: E501
                'BTC': get_asset_balance_total(A_BTC, setup),
                'EUR': get_asset_balance_total(A_EUR, setup),
                A_RDN.identifier: get_asset_balance_total(A_RDN, setup),
            }
            for index, entry in enumerate(result):
                assert len(entry) == 5
                assert entry['time'] >= start_time
                assert entry['category'] == 'asset'
                assert entry['usd_value'] is not None
                assert FVal(entry['amount']) == totals[entry['asset']]
                # check that the usd_value is in descending order
                if index == 0:
                    continue
                assert FVal(result[index - 1]['usd_value']) > FVal(entry['usd_value'])
        else:
            assert len(result) == 5
            totals = {
                'ETH': get_asset_balance_total(A_ETH, setup),
                'ETH2': get_asset_balance_total(A_ETH2, setup),
                'BTC': get_asset_balance_total(A_BTC, setup),
                'EUR': get_asset_balance_total(A_EUR, setup),
                A_RDN.identifier: get_asset_balance_total(A_RDN, setup),
            }
            for index, entry in enumerate(result):
                assert len(entry) == 5
                assert entry['time'] >= start_time
                assert entry['category'] == 'asset'
                assert entry['usd_value'] is not None
                assert FVal(entry['amount']) == totals[entry['asset']]
                # check that the usd_value is in descending order
                if index == 0:
                    continue
                assert FVal(result[index - 1]['usd_value']) > FVal(entry['usd_value'])
    else:
        assert_error_response(
            response=response,
            contained_in_msg='logged in user testuser does not have a premium subscription',
            status_code=HTTPStatus.FORBIDDEN,
        )


@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_query_statistics_value_distribution_errors(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that the statistics value distribution endpoint handles errors properly"""
    # Test omitting the distribution_by argument
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'statisticsvaluedistributionresource',
        ),
    )
    assert_error_response(
        response=response,
        contained_in_msg='Missing data for required field',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Test invalid value for distribution_by
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server,
            'statisticsvaluedistributionresource',
        ), json={'distribution_by': 'haircolor'},
    )
    assert_error_response(
        response=response,
        contained_in_msg='Must be one of: location, asset',
        status_code=HTTPStatus.BAD_REQUEST,
    )


@pytest.mark.parametrize('start_with_valid_premium', [True, False])
def test_query_statistics_renderer(
        rotkehlchen_api_server: 'APIServer',
        start_with_valid_premium: bool,
    ) -> None:
    """Test that the statistics renderer endpoint works when properly queried"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    if start_with_valid_premium:
        def mock_premium_get(url: str, *_args: Any, **_kwargs: Any) -> MockResponse:
            if 'last_data_metadata' in url:
                response = (
                    '{"upload_ts": 0, "last_modify_ts": 0, "data_hash": "0x0", "data_size": 0}'
                )
            else:
                response = '{"data": "codegoeshere"}'
            return MockResponse(200, response)

        assert rotki.premium is not None
        premium_patch: Any = patch.object(rotki.premium.session, 'get', mock_premium_get)
    else:
        premium_patch = contextlib.nullcontext()

    with premium_patch:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'statisticsrendererresource',
            ),
        )
    if start_with_valid_premium:
        result = assert_proper_sync_response_with_result(response)
        assert result == 'codegoeshere'
    else:
        assert_error_response(
            response=response,
            contained_in_msg='logged in user testuser does not have a premium subscription',
            status_code=HTTPStatus.FORBIDDEN,
        )


@pytest.mark.parametrize('ethereum_accounts', [['0x01471dB828Cfb96Dcf215c57a7a6493702031EC1']])
@pytest.mark.parametrize('base_accounts', [['0x01471dB828Cfb96Dcf215c57a7a6493702031EC1']])
def test_query_events_analysis(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list[ChecksumEvmAddress],
) -> None:
    """Test that information returned by the yearly event analysis endpoint is correct.
    It adds:
    - transactions
    - evm events (for fees)
    - gnosis payments
    - swap events

    Some of them are outside the queried range to confirm that the range is correct.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    assert_proper_sync_response_with_result(response=requests.post(  # Test that there is no failure for no data  # noqa: E501
        url=api_url_for(rotkehlchen_api_server, 'eventsanalysisresource'),
        json={'from_timestamp': 1704067200, 'to_timestamp': 1735689599},
    ))

    events_db = DBHistoryEvents(db)
    with db.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[
                *create_swap_events(
                    timestamp=TimestampMS(1718562595000),
                    location=Location.KRAKEN,
                    event_identifier='1xyz',
                    spend=AssetAmount(asset=A_BTC, amount=ONE),
                    receive=AssetAmount(asset=A_ETH, amount=ONE),
                    fee=AssetAmount(asset=A_BTC, amount=FVal('0.1')),
                ), *create_swap_events(
                    timestamp=TimestampMS(1734373795000),
                    location=Location.COINBASE,
                    event_identifier='2xyz',
                    spend=AssetAmount(asset=A_BTC, amount=FVal(2)),
                    receive=AssetAmount(asset=A_ETH, amount=FVal(2)),
                    fee=AssetAmount(asset=A_BTC, amount=FVal('0.1')),
                ), *create_swap_events(
                    timestamp=TimestampMS(1734373795000),
                    location=Location.EXTERNAL,
                    event_identifier='3xyz',
                    spend=AssetAmount(asset=A_BTC, amount=FVal(2)),
                    receive=AssetAmount(asset=A_ETH, amount=FVal(2)),
                    fee=AssetAmount(asset=A_BTC, amount=FVal('0.1')),
                ), *create_swap_events(
                    timestamp=TimestampMS(1702751395000),  # last year
                    location=Location.EXTERNAL,
                    event_identifier='4xyz',
                    spend=AssetAmount(asset=A_BTC, amount=FVal(2)),
                    receive=AssetAmount(asset=A_ETH, amount=FVal(2)),
                    fee=AssetAmount(asset=A_BTC, amount=FVal('0.1')),
                ),
            ],
        )

        db.add_to_ignored_assets(write_cursor=write_cursor, asset=A_USDC)
        tx_hash1, tx_hash2, tx_hash3, tx_hash4 = make_evm_tx_hash(), make_evm_tx_hash(), make_evm_tx_hash(), make_evm_tx_hash()  # noqa: E501
        tx_hash_to_chain = {
            make_evm_tx_hash(): Location.ETHEREUM,
            make_evm_tx_hash(): Location.BASE,
            make_evm_tx_hash(): Location.ARBITRUM_ONE,
        }
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[
                EvmEvent(
                    tx_ref=tx_hash,
                    sequence_index=1,
                    timestamp=TimestampMS(1734373795000),
                    location=chain,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=A_ETH,
                    amount=FVal(0.1),
                    counterparty=CPT_GAS,
                    location_label=ethereum_accounts[0],
                )
            for tx_hash, chain in tx_hash_to_chain.items()] + [
                EvmEvent(  # event happening last year
                    tx_ref=tx_hash1,
                    sequence_index=1,
                    timestamp=TimestampMS(1702751395000),
                    location=Location.BASE,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=A_ETH,
                    amount=FVal(5),
                    counterparty=CPT_GAS,
                    location_label=ethereum_accounts[0],
                ),
                EvmEvent(  # event to test counterparties
                    tx_ref=tx_hash2,
                    sequence_index=1,
                    timestamp=TimestampMS(1734373795000),
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=A_ETH,
                    amount=FVal(0.1),
                    counterparty=CPT_ENS,
                    location_label=ethereum_accounts[0],
                ),
                EvmEvent(  # second event with the same tx hash - should not be counted separately
                    tx_ref=tx_hash2,
                    sequence_index=2,
                    timestamp=TimestampMS(1734373795000),
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=A_ETH,
                    amount=FVal(0.1),
                    location_label=ethereum_accounts[0],
                ),
                EvmEvent(  # event with ignored asset
                    tx_ref=tx_hash3,
                    sequence_index=1,
                    timestamp=TimestampMS(1734373795000),
                    location=Location.GNOSIS,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.NONE,
                    asset=A_USDC,
                    amount=FVal(5),
                    location_label=ethereum_accounts[0],
                ),
                EvmEvent(  # ENS event outside date range - should not be counted
                    tx_ref=tx_hash4,
                    sequence_index=1,
                    timestamp=TimestampMS(1640995200000),  # 2022 - outside range
                    location=Location.ETHEREUM,
                    event_type=HistoryEventType.SPEND,
                    event_subtype=HistoryEventSubType.FEE,
                    asset=A_ETH,
                    amount=FVal(0.1),
                    counterparty=CPT_ENS,
                    location_label=ethereum_accounts[0],
                ),
            ],
        )

        dbevmtx = DBEvmTx(db)
        dbevmtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[EvmTransaction(
                tx_hash=tx_hash,
                chain_id=ChainID(chain.to_chain_id()),
                timestamp=Timestamp(1718562595),
                block_number=3,
                from_address=make_evm_address(),
                to_address=make_evm_address(),
                value=4000000,
                gas=5000000,
                gas_price=2000000000,
                gas_used=25000000,
                input_data=b'',
                nonce=1,
            ) for tx_hash, chain in tx_hash_to_chain.items()],
            relevant_address=ethereum_accounts[0],
        )

        dbevmtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[EvmTransaction(
                tx_hash=tx_hash1,
                chain_id=chain,
                timestamp=Timestamp(1702751395),  # timestamp outside the range
                block_number=3,
                from_address=make_evm_address(),
                to_address=make_evm_address(),
                value=4000000,
                gas=5000000,
                gas_price=2000000000,
                gas_used=25000000,
                input_data=b'',
                nonce=1,
            ) for chain in (ChainID.ETHEREUM,)],
            relevant_address=ethereum_accounts[0],
        )

        dbevmtx.add_transactions(
            write_cursor=write_cursor,
            evm_transactions=[
                EvmTransaction(
                    tx_hash=tx_hash3,  # tx corresponding to the event with an ignored asset
                    chain_id=ChainID.GNOSIS,
                    timestamp=Timestamp(1718562595),
                    block_number=3,
                    from_address=make_evm_address(),
                    to_address=make_evm_address(),
                    value=4000000,
                    gas=5000000,
                    gas_price=2000000000,
                    gas_used=25000000,
                    input_data=b'',
                    nonce=1,
                ),
                EvmTransaction(
                    tx_hash=tx_hash4,  # tx for ENS event outside date range
                    chain_id=ChainID.ETHEREUM,
                    timestamp=Timestamp(1640995200),  # 2022 - outside range
                    block_number=4,
                    from_address=make_evm_address(),
                    to_address=make_evm_address(),
                    value=0,
                    gas=21000,
                    gas_price=20000000000,
                    gas_used=21000,
                    input_data=b'',
                    nonce=4,
                ),
            ],
            relevant_address=ethereum_accounts[0],
        )

        write_cursor.execute(
            'INSERT OR REPLACE INTO gnosispay_data(tx_hash, timestamp, merchant_name, '
            'merchant_city, country, mcc, transaction_symbol, transaction_amount, '
            'billing_symbol, billing_amount, reversal_symbol, reversal_amount) '
            'VALUES(?, ?, ?, ?, ? ,?, ?, ?, ?, ?, ?, ?)',
            (
                deserialize_evm_tx_hash('0xb3be0391a753de5ef54b6b43c716240e1cb2a4a0a1120420f5ce168fdd08f17c'),
                1726712020, 'Acme Inc.',
                'Sevilla', 'ES', 6666,
                'EUR', '42.24',
                None, None,
                'EUR', '2.35',
            ),
        )

    response = requests.post(
        url=api_url_for(rotkehlchen_api_server, 'eventsanalysisresource'),
        json={'from_timestamp': 1704067200, 'to_timestamp': 1735689599},
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['trades_by_exchange'] == {'external': 1, 'kraken': 1, 'coinbase': 1}
    assert FVal(result['eth_on_gas']).is_close('0.3')
    assert FVal(result['eth_on_gas_per_address'][ethereum_accounts[0]]).is_close('0.3')
    assert result['transactions_per_chain'] == {
        'ARBITRUM_ONE': 1,
        'ETHEREUM': 1,
        'BASE': 1,
    }
    assert result['top_days_by_number_of_transactions'] == [
        {'timestamp': 1734307200, 'amount': '4'},
    ]
    assert result['gnosis_max_payments_by_currency'] == [{'symbol': 'EUR', 'amount': '42.24'}]
    assert result['transactions_per_protocol'] == [{'protocol': 'ens', 'transactions': 1}]
    assert result['score'] == 1684


def test_wrap_stats_counts_non_evm_chains(
        rotkehlchen_api_server: 'APIServer',
) -> None:
    """Ensure wrap stats include Solana and Bitcoin transaction counts."""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    db = rotki.data.db
    events_db = DBHistoryEvents(db)
    with db.conn.write_ctx() as write_cursor:
        events_db.add_history_events(
            write_cursor=write_cursor,
            history=[SolanaEvent(
                tx_ref=make_solana_signature(),
                sequence_index=0,
                timestamp=(ts_ms := TimestampMS(1609459200000)),
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_SOL,
                amount=ONE,
                location_label=str(make_solana_address()),
            ), HistoryEvent(
                event_identifier=f'{BTC_EVENT_IDENTIFIER_PREFIX}{make_btc_tx_id()}',
                sequence_index=0,
                timestamp=ts_ms,
                location=Location.BITCOIN,
                event_type=HistoryEventType.RECEIVE,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_BTC,
                amount=ONE,
                location_label=str(UNIT_BTC_ADDRESS1),
            )],
        )

    response = requests.post(
        url=api_url_for(rotkehlchen_api_server, 'eventsanalysisresource'),
        json={'from_timestamp': 1609459200, 'to_timestamp': 1609459800},
    )
    result = assert_proper_sync_response_with_result(response)
    transactions_per_chain = result['transactions_per_chain']
    assert transactions_per_chain.get(SupportedBlockchain.SOLANA.name) == 1
    assert transactions_per_chain.get(SupportedBlockchain.BITCOIN.name) == 1
