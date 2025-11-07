from typing import TYPE_CHECKING

import pytest
import requests

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH, A_EUR
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryEvent
from rotkehlchen.history.events.structures.swap import create_swap_events
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_sync_response_with_result
from rotkehlchen.tests.utils.exchanges import mock_exchange_data_in_db
from rotkehlchen.tests.utils.factories import make_evm_address
from rotkehlchen.types import (
    EVM_LOCATIONS_TYPE,
    AssetAmount,
    BTCAddress,
    ChecksumEvmAddress,
    Location,
    TimestampMS,
)

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer

UNISWAP_ADDR = string_to_evm_address('0xcaf012cB72f2c7152b255E091837E3a628F739e7')


@pytest.mark.parametrize('added_exchanges', [(Location.BINANCE, Location.POLONIEX)])
@pytest.mark.parametrize('ethereum_accounts', [[UNISWAP_ADDR]])
@pytest.mark.parametrize('ethereum_modules', [['uniswap']])
@pytest.mark.parametrize('start_with_valid_premium', [True])
def test_get_associated_locations(
        rotkehlchen_api_server_with_exchanges: 'APIServer',
        added_exchanges: list[EVM_LOCATIONS_TYPE],
        ethereum_accounts: list[ChecksumEvmAddress],  # pylint: disable=unused-argument
        start_with_valid_premium: bool,  # pylint: disable=unused-argument
) -> None:
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    mock_exchange_data_in_db(added_exchanges, rotki)
    db = rotki.data.db
    with db.user_write() as cursor:
        DBHistoryEvents(db).add_history_events(
            write_cursor=cursor,
            history=create_swap_events(
                timestamp=TimestampMS(1595833195000),
                location=Location.NEXO,
                spend=AssetAmount(asset=A_EUR, amount=ONE),
                receive=AssetAmount(asset=A_ETH, amount=FVal('281.14')),
                group_identifier='tradeid',
            ))

    # get locations
    response = requests.get(
        api_url_for(
            rotkehlchen_api_server_with_exchanges,
            'associatedlocations',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    assert set(result) == {'nexo', 'binance', 'poloniex'}


@pytest.mark.parametrize('ethereum_accounts', [['0x9DBE4Eb4A0a41955E1DC733E322f84295a0aa5c0']])
@pytest.mark.parametrize('btc_accounts', [['bc1qdf3av8da4up78shctfual6j6cv3kyvcw6qk3fz']])
def test_get_location_labels(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        btc_accounts: list['BTCAddress'],
) -> None:
    """Test that location labels endpoint returns labels ordered by frequency."""
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db

    # Create events with different frequencies
    events = []
    for count, location_label, location in (
        (4, (eth_address := ethereum_accounts[0]), Location.ETHEREUM),
        (3, 'Kraken 1', Location.KRAKEN),
        (2, 'Binance Account', Location.BINANCE),
        (2, (btc_address := btc_accounts[0]), Location.BITCOIN),
        (1, 'Kraken 2', Location.KRAKEN),
    ):
        events.extend([HistoryEvent(
            group_identifier=f'xyz_{location_label}_{idx}',
            sequence_index=idx,
            timestamp=TimestampMS(1500000000000 + idx),
            location=location,
            asset=A_ETH,
            amount=ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.NONE,
            location_label=location_label,
        ) for idx in range(count)])

    with db.user_write() as cursor:
        DBHistoryEvents(db).add_history_events(write_cursor=cursor, history=events)

    result = assert_proper_sync_response_with_result(
        response=requests.get(api_url_for(rotkehlchen_api_server, 'locationlabelsresource')),
    )

    # Check that we get the correct format with location_label and location
    # Results should be ordered by frequency (descending)
    # Only tracked blockchain accounts and all exchange accounts should appear
    assert len(result) == 5
    expected_results = [
        {'location_label': eth_address, 'location': 'ethereum'},  # 4 occurrences
        {'location_label': 'Kraken 1', 'location': 'kraken'},  # 3 occurrences
        {'location_label': btc_address, 'location': 'bitcoin'},  # 2 occurrences
        {'location_label': 'Binance Account', 'location': 'binance'},  # 2 occurrences
        {'location_label': 'Kraken 2', 'location': 'kraken'},  # 1 occurrence (exchanges don't need credentials)  # noqa: E501
    ]
    assert result == expected_results


@pytest.mark.parametrize('ethereum_accounts', [['0x9DBE4Eb4A0a41955E1DC733E322f84295a0aa5c0']])
def test_get_location_labels_excludes_untracked_accounts(
        rotkehlchen_api_server: 'APIServer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that location labels endpoint excludes untracked blockchain accounts"""
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db

    # Create events for tracked and untracked addresses
    with db.user_write() as cursor:
        DBHistoryEvents(db).add_history_events(write_cursor=cursor, history=[
            HistoryEvent(
                group_identifier='tracked_event',
                sequence_index=0,
                timestamp=TimestampMS(1500000000000),
                location=Location.ETHEREUM,
                asset=A_ETH,
                amount=ONE,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                location_label=(tracked_address := ethereum_accounts[0]),
            ), HistoryEvent(
                group_identifier='untracked_event',
                sequence_index=0,
                timestamp=TimestampMS(1500000000000),
                location=Location.ETHEREUM,
                asset=A_ETH,
                amount=ONE,
                event_type=HistoryEventType.INFORMATIONAL,
                event_subtype=HistoryEventSubType.APPROVE,
                location_label=make_evm_address(),
            ),
        ])

    result = assert_proper_sync_response_with_result(
        requests.get(api_url_for(
            rotkehlchen_api_server,
            'locationlabelsresource'),
        ),
    )

    # Should only return the tracked address, not the untracked one
    assert len(result) == 1
    assert result[0]['location_label'] == tracked_address
    assert result[0]['location'] == 'ethereum'
