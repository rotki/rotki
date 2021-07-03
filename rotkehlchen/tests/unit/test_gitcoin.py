from pathlib import Path

import pytest

from rotkehlchen.accounting.ledger_actions import (
    GitcoinEventData,
    GitcoinEventTxType,
    LedgerAction,
    LedgerActionType,
)
from rotkehlchen.chain.ethereum.gitcoin.importer import GitcoinDataImporter
from rotkehlchen.constants.assets import A_ETH, A_USD
from rotkehlchen.fval import FVal
from rotkehlchen.tests.utils.history import prices
from rotkehlchen.typing import Location, Timestamp


@pytest.mark.parametrize('mocked_price_queries', [prices])
def test_csv_import(database, price_historian):  # pylint: disable=unused-argument
    imp = GitcoinDataImporter(database)
    csv_path = Path(__file__).resolve().parent.parent / 'data' / 'gitcoin.csv'
    imp.import_gitcoin_csv(csv_path)

    actions = imp.db_ledger.get_ledger_actions(from_ts=None, to_ts=None, location=Location.GITCOIN)

    assert len(actions) == 10
    expected_actions = [LedgerAction(
        identifier=1,
        timestamp=Timestamp(1624791600),
        action_type=LedgerActionType.DONATION_RECEIVED,
        location=Location.GITCOIN,
        amount=FVal('0.0004789924016679019628604417823'),
        asset=A_ETH,
        rate=FVal('1983.33'),
        rate_asset=A_USD,
        link='0x00298f72ad40167051e111e6dc2924de08cce7cf0ad00d04ad5a9e58426536a1',
        notes='Gitcoin grant 149 event',
        extra_data=GitcoinEventData(
            tx_id='0x00298f72ad40167051e111e6dc2924de08cce7cf0ad00d04ad5a9e58426536a1',
            grant_id=149,
            tx_type=GitcoinEventTxType.ETHEREUM,
        ),
    ), LedgerAction(
        identifier=2,
        timestamp=Timestamp(1624791600),
        action_type=LedgerActionType.DONATION_RECEIVED,
        location=Location.GITCOIN,
        amount=FVal('0.0005092445533521905078832065264'),
        asset=A_ETH,
        rate=FVal('1983.33'),
        rate_asset=A_USD,
        link='sync-tx:5612f84bc20cda25b911af39b792c973bdd5916b3b6868db2420b5dafd705a90',
        notes='Gitcoin grant 149 event',
        extra_data=GitcoinEventData(
            tx_id='5612f84bc20cda25b911af39b792c973bdd5916b3b6868db2420b5dafd705a90',
            grant_id=149,
            tx_type=GitcoinEventTxType.ZKSYNC,
        ),
    )]
    assert expected_actions == actions[:2]
