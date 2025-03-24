import csv
import string
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import patch

import pytest
import requests

from rotkehlchen.accounting.export.csv import FILENAME_SKIPPED_EXTERNAL_EVENTS_CSV
from rotkehlchen.assets.asset import CryptoAsset
from rotkehlchen.assets.types import AssetType
from rotkehlchen.constants import ONE
from rotkehlchen.globaldb.handler import GlobalDBHandler
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.exchanges import try_get_first_exchange
from rotkehlchen.tests.utils.kraken import KRAKEN_GENERAL_LEDGER_RESPONSE, MockKraken
from rotkehlchen.types import Location, Timestamp

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('added_exchanges', [(Location.KRAKEN,)])
def test_skipped_external_events(
        rotkehlchen_api_server_with_exchanges: 'APIServer',
        globaldb: GlobalDBHandler,
        tmpdir_factory: pytest.TempdirFactory,
    ) -> None:
    server = rotkehlchen_api_server_with_exchanges
    rotki = rotkehlchen_api_server_with_exchanges.rest_api.rotkehlchen
    # The input has extra information to test that the filters work correctly.
    # The events related to staking are AAA, BBB and CCC, DDD
    input_ledger = """
    {
    "ledger":{
        "WWW": {
            "refid": "WWWWWWW",
            "time": 1640493376.4008,
            "type": "staking",
            "subtype": "",
            "aclass": "currency",
            "asset": "XTZ",
            "amount": "0.0000100000",
            "fee": "0.0000000000",
            "balance": "0.0000100000"
        },
        "AAA": {
            "refid": "XXXXXX",
            "time": 1640493374.4008,
            "type": "staking",
            "subtype": "",
            "aclass": "currency",
            "asset": "NEWASSET",
            "amount": "0.0000538620",
            "fee": "0.0000000000",
            "balance": "0.0003349820"
        },
        "BBB": {
            "refid": "YYYYYYYY",
            "time": 1636740198.9674,
            "type": "staking",
            "subtype": "stakingfromspot",
            "aclass": "currency",
            "asset": "ETH2.S",
            "amount": "0.0600000000",
            "fee": "0.0000000000",
            "balance": "0.0600000000"
        },
        "CCC": {
            "refid": "YYYYYYYY",
            "time": 1636740198.9674,
            "type": "staking",
            "subtype": "stakingfromspot",
            "aclass": "currency",
            "asset": "NEWASSET",
            "amount": "0.0600000000",
            "fee": "0.0000000000",
            "balance": "0.0600000000"
        },
        "DDD": {
            "refid": "ZZZZZZZZZ",
            "time": 1636750198.9674,
            "type": "staking",
            "subtype": "stakingtospot",
            "aclass": "currency",
            "asset": "NEWASSET",
            "amount": "0.0600000000",
            "fee": "0.0000000000",
            "balance": "0.0600000000"
        }
    },
    "count": 5
    }
    """
    # Test that before populating we don't have any event
    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    assert len(result['entries']) == 0

    with rotki.data.db.user_write() as write_cursor:
        rotki.data.db.purge_exchange_data(write_cursor, Location.KRAKEN)
    target = 'rotkehlchen.tests.utils.kraken.KRAKEN_GENERAL_LEDGER_RESPONSE'
    kraken: MockKraken = cast('MockKraken', try_get_first_exchange(
        rotki.exchange_manager, Location.KRAKEN,
        ))
    assert kraken is not None
    kraken.random_ledgers_data = False
    with patch(target, new=input_ledger):
        kraken.query_history_events()

    # check staking events
    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
        json={
            'from_timestamp': 1636538550,
            'to_timestamp': 1640493378,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    events = result['entries']
    assert len(events) == 1, 'only 1 event should have been found now and rest written to skipped'

    # now check that we have populated skipped events
    response = requests.get(
        api_url_for(server, 'historyskippedexternaleventresource'),
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['total'] == 6  # 5 is due to +2 unknown assets set up during fixture
    assert result['locations']['kraken'] == 6
    assert len(result['locations']) == 1

    # now let's test the export skipped external events endpoint
    flat_general = KRAKEN_GENERAL_LEDGER_RESPONSE.translate({ord(c): None for c in string.whitespace})  # noqa: E501
    flat_stake = input_ledger.translate({ord(c): None for c in string.whitespace})

    export_dir = Path(tmpdir_factory.mktemp('test_csv_dir'))
    response = requests.put(
        api_url_for(server, 'historyskippedexternaleventresource'),
        json={'directory_path': str(export_dir)},
    )
    assert_simple_ok_response(response)
    with open(export_dir / FILENAME_SKIPPED_EXTERNAL_EVENTS_CSV, newline='', encoding='utf-8') as csvfile:  # noqa: E501
        reader = csv.DictReader(csvfile)
        count = 0
        for row in reader:
            count += 1
            assert row['location'] == 'kraken'
            assert row['extra_data'] == '{"location_label":"mockkraken"}'
            if 'D3' in row['data'] or 'W3' in row['data']:
                assert row['data'] in flat_general
            else:
                assert row['data'] in flat_stake
    assert count == 6

    # now try to reprocess the skipped events after adding the asset to the kraken mapping
    globaldb.add_asset(CryptoAsset.initialize(
        identifier='NEWASSET',
        asset_type=AssetType.OWN_CHAIN,
        name='NEWASSET_NAME',
        symbol='NEWASSET',
        started=Timestamp(0),
    ))
    with rotki.data.db.user_write() as write_cursor:
        rotki.data.db.add_asset_identifiers(write_cursor=write_cursor, asset_identifiers=['NEWASSET'])  # noqa: E501
    response = requests.post(
        api_url_for(server, 'historyskippedexternaleventresource'),
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['total'] == 6
    assert result['successful'] == 4
    response = requests.get(
        api_url_for(server, 'historyskippedexternaleventresource'),
    )
    result = assert_proper_sync_response_with_result(response)
    assert result['total'] == 2, 'only 2 skipped events should be left'
    assert result['locations']['kraken'] == 2, 'only 2 skipped events should be left'
    assert len(result['locations']) == 1

    # and finally check that the staking events have increased
    response = requests.post(
        api_url_for(
            server,
            'stakingresource',
        ),
        json={
            'from_timestamp': 1636538550,
            'to_timestamp': 1640493378,
        },
    )
    result = assert_proper_sync_response_with_result(response)
    events = result['entries']
    assert len(events) == 3
