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
from rotkehlchen.types import (
    EVM_LOCATIONS_TYPE,
    AssetAmount,
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
                event_identifier='tradeid',
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


def test_get_location_labels(rotkehlchen_api_server: 'APIServer') -> None:
    """Test that the location labels endpoint returns all the labels used in the DB."""
    db = rotkehlchen_api_server.rest_api.rotkehlchen.data.db
    labels = ['Kraken 1', 'Kraken 2', 'some other random label']
    with db.user_write() as cursor:
        DBHistoryEvents(db).add_history_events(
            write_cursor=cursor,
            history=[HistoryEvent(
                event_identifier=f'xyz{location_label}',
                sequence_index=0,
                timestamp=TimestampMS(1500000000000),
                location=Location.KRAKEN,
                asset=A_EUR,
                amount=ONE,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                location_label=location_label,
            ) for location_label in labels])

    assert assert_proper_sync_response_with_result(
        response=requests.get(api_url_for(rotkehlchen_api_server, 'locationlabelsresource')),
    ) == labels
