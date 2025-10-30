from unittest.mock import patch

import pytest

from rotkehlchen.chain.gnosis.decoding.decoder import GnosisTransactionDecoder
from rotkehlchen.chain.gnosis.modules.gnosis_pay.constants import (
    CPT_GNOSIS_PAY,
    GNOSIS_PAY_CASHBACK_ADDRESS,
    GNOSIS_PAY_REFERRAL_ADDRESS,
    GNOSIS_PAY_SPENDING_COLLECTOR,
)
from rotkehlchen.chain.gnosis.transactions import GnosisTransactions
from rotkehlchen.constants.assets import Asset
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.factories import make_evm_tx_hash
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    ApiKey,
    ExternalService,
    ExternalServiceApiCredentials,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import ts_ms_to_sec


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0x7EcB43E01425c66a783A3065F782ccF304b39B99']])
def test_gnosis_pay_cashback(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x1c6f58c55ba2eeef7e08ed4725d16ae479d1b4210b39e647a9b282af6ffb9470')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
    )
    amount = '0.8527869407'
    assert events == [
        EvmEvent(
            sequence_index=8,
            timestamp=TimestampMS(1726146635000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.CASHBACK,
            asset=Asset('eip155:100/erc20:0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb'),
            amount=FVal(amount),
            location_label=gnosis_accounts[0],
            notes=f'Receive cashback of {amount} GNO from Gnosis Pay',
            tx_ref=tx_hash,
            counterparty=CPT_GNOSIS_PAY,
            address=GNOSIS_PAY_CASHBACK_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [[
    '0xc746598C9dD7FC62EF8775445F2F375aCbaCa7AE',  # user's gnosis pay safe
]])
def test_gnosis_pay_referral(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc778b8c23b823d6cec199ece516ab68658c7caafb508104f2a0c9de4d0358529')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
    )
    amount = '30.23'
    assert events == [
        EvmEvent(
            sequence_index=18,
            timestamp=TimestampMS(1727856180000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430'),
            amount=FVal(amount),
            location_label=gnosis_accounts[0],
            notes=f'Receive referral reward of {amount} EURe from Gnosis Pay',
            tx_ref=tx_hash,
            counterparty=CPT_GNOSIS_PAY,
            address=GNOSIS_PAY_REFERRAL_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [[
    '0xF4a1fB1689104479De1EcADfA472A9B866D08B16',  # user's gnosis pay safe
]])
def test_gnosis_pay_spend(gnosis_inquirer, gnosis_accounts, rotki_premium_object):
    tx_hash = deserialize_evm_tx_hash('0xe8d666d6acf22e5a50dfea7ece1473558a854dfa04441ea9b3d0898843364ad8')  # noqa: E501
    events, gnosis_txs_decoder = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
    )
    gnosispay_decoder = gnosis_txs_decoder.decoders.get('GnosisPay')
    gnosis_txs_decoder.premium = rotki_premium_object
    amount = '8.5'
    expected_events = [
        EvmEvent(
            sequence_index=29,
            timestamp=TimestampMS(1726590745000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYMENT,
            asset=Asset('eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430'),
            amount=FVal(amount),
            location_label=gnosis_accounts[0],
            notes=f'Spend {amount} EURe via Gnosis Pay',
            tx_ref=tx_hash,
            counterparty=CPT_GNOSIS_PAY,
            address=GNOSIS_PAY_SPENDING_COLLECTOR,
        ),
    ]
    assert events == expected_events

    with gnosis_inquirer.database.user_write() as write_cursor:
        gnosis_inquirer.database.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(service=ExternalService.GNOSIS_PAY, api_key=ApiKey('foo'))],  # noqa: E501
        )
    gnosispay_decoder.reload_data()

    responses = iter([
        MockResponse(200, """{"results" :[{
        "createdAt": "2024-09-17T16:32:25.0000Z",
        "transactionAmount": "850",
        "transactionCurrency": {
            "symbol": "EUR",
            "code": "978",
            "decimals": 2,
            "name": "Euro"
        },
        "billingAmount": "850",
        "billingCurrency": {
            "symbol": "EUR",
            "code": "978",
            "decimals": 2,
            "name": "Euro"
        },
        "mcc": "5411",
        "merchant": {
            "name": "Lidl sagt Danke          ",
            "city": "Berlin       ",
            "country": {
                "name": "Germany",
                "numeric": "276",
                "alpha2": "DE",
                "alpha3": "DEU"
            }
        },
        "country": {
            "name": "Germany",
            "numeric": "276",
            "alpha2": "DE",
            "alpha3": "DEU"
        },
        "transactions": [
            {
                "status": "ExecSuccess",
                "to": "0xbooooooooo",
                "value": "0",
                "data": "0xfooooooooooo",
                "hash": "0xe8d666d6acf22e5a50dfea7ece1473558a854dfa04441ea9b3d0898843364ad8"
            }
        ],
        "kind": "Payment",
        "status": "Approved"
        }]}"""),
        MockResponse(200, """{"results": []}"""),
    ])

    def mock_gnosispay_api(url, **kwargs):  # pylint: disable=unused-argument
        try:
            return next(responses)
        except StopIteration as e:
            raise AssertionError('Unexpected extra Gnosis Pay API call during test') from e

    with patch.object(
            gnosis_txs_decoder,  # do not reload data since this overwrites the api object
            'reload_data',
            lambda x: None,
    ), patch.object(
            gnosispay_decoder.gnosispay_api.session,  # mock api response
            'get',
            side_effect=mock_gnosispay_api,
    ):
        events = gnosis_txs_decoder.decode_and_get_transaction_hashes(ignore_cache=True, tx_hashes=[tx_hash])  # noqa: E501

    with gnosis_inquirer.database.conn.read_ctx() as cursor:
        refreshed_events = DBHistoryEvents(gnosis_inquirer.database).get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(tx_hashes=[tx_hash]),
        )

        expected_events[0].identifier = 1
        expected_events[0].notes = 'Pay 8.5 EUR to Lidl sagt Danke in Berlin :country:DE:'
    assert refreshed_events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [[
    '0x49e52a677BD19E50beE3642a8050A5A08a6EC697',  # user's gnosis pay safe
]])
def test_gnosis_pay_refund(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x5f659bbc5214b358ffa5474c4209fad0587b7a9735b5965e7475c2bcb893ad38')  # noqa: E501
    events, gnosis_txs_decoder = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
    )
    gnosispay_decoder = gnosis_txs_decoder.decoders.get('GnosisPay')

    amount = '2.35'
    expected_events = [
        EvmEvent(
            sequence_index=10,
            timestamp=TimestampMS(1726832020000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REFUND,
            asset=Asset('eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430'),
            amount=FVal(amount),
            location_label=gnosis_accounts[0],
            notes=f'Receive refund of {amount} EURe from Gnosis Pay',
            tx_ref=tx_hash,
            counterparty=CPT_GNOSIS_PAY,
            address=GNOSIS_PAY_SPENDING_COLLECTOR,
        ),
    ]
    assert events == expected_events

    # and now let's mock the api having gnosis pay refund data in the DB matching the
    with gnosis_inquirer.database.user_write() as write_cursor:
        gnosis_inquirer.database.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(service=ExternalService.GNOSIS_PAY, api_key=ApiKey('foo'))],  # noqa: E501
        )
        gnosispay_decoder.reload_data()
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

    # do not reload data since this overwrites the api object
    with patch.object(gnosis_txs_decoder, 'reload_data', lambda x: None):
        events = gnosis_txs_decoder.decode_and_get_transaction_hashes(ignore_cache=True, tx_hashes=[tx_hash])  # noqa: E501

    expected_events[0].notes = 'Receive refund of 2.35 EUR from Acme Inc. in Sevilla :country:ES:'
    assert events == expected_events


@pytest.mark.parametrize('gnosis_accounts', [[
    '0xc746598C9dD7FC62EF8775445F2F375aCbaCa7AE',
]])
@pytest.mark.freeze_time('2023-11-14 22:30:00 GMT')
def test_backfill_missing_gnosis_pay_events(gnosis_inquirer, gnosis_accounts):
    tx_hash, second_tx_hash = make_evm_tx_hash(), make_evm_tx_hash()
    second_note = 'Pay 1.4 EUR to AUTOPISTA R4 SEITT -2 in MADRID :country:ES:'
    gnosis_transactions = GnosisTransactions(
        gnosis_inquirer=gnosis_inquirer,
        database=gnosis_inquirer.database,
    )
    gnosis_decoder = GnosisTransactionDecoder(
        database=gnosis_inquirer.database,
        gnosis_inquirer=gnosis_inquirer,
        transactions=gnosis_transactions,
    )

    gnosispay_decoder = gnosis_decoder.decoders.get('GnosisPay')
    assert gnosispay_decoder is not None

    with gnosis_inquirer.database.user_write() as write_cursor:
        gnosis_inquirer.database.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(service=ExternalService.GNOSIS_PAY, api_key=ApiKey('foo'))],  # noqa: E501
        )

    gnosispay_decoder.reload_data()
    assert gnosispay_decoder.gnosispay_api is not None

    timestamp_ms = TimestampMS(1700000000000)
    with gnosis_inquirer.database.user_write() as write_cursor:
        write_cursor.executemany(
            'INSERT INTO history_events('
            'identifier, entry_type, event_identifier, sequence_index, notes, timestamp, '
            'location, asset, amount, type, subtype, ignored'
            ') VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)',
            [
                (
                    None,
                    HistoryBaseEntryType.HISTORY_EVENT.value,
                    'evm-gnosis-1',
                    0,
                    'Spend 1 EURe via Gnosis Pay',
                    timestamp_ms,
                    Location.GNOSIS.serialize_for_db(),
                    'ETH',
                    '1',
                    HistoryEventType.RECEIVE.serialize(),
                    HistoryEventSubType.NONE.serialize(),
                ),
                (
                    None,
                    HistoryBaseEntryType.HISTORY_EVENT.value,
                    'evm-gnosis-2',
                    1,
                    second_note,
                    timestamp_ms,
                    Location.GNOSIS.serialize_for_db(),
                    'eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430',
                    '1.4',
                    HistoryEventType.SPEND.serialize(),
                    HistoryEventSubType.NONE.serialize(),
                ),
            ],
        )
        write_cursor.execute(
            'SELECT identifier FROM history_events WHERE event_identifier=?',
            ('evm-gnosis-1',),
        )
        identifier = write_cursor.fetchone()[0]
        write_cursor.execute(
            'INSERT INTO chain_events_info(identifier, tx_ref, counterparty) VALUES (?, ?, ?)',
            (identifier, tx_hash, CPT_GNOSIS_PAY),
        )
        write_cursor.execute(
            'SELECT identifier FROM history_events WHERE event_identifier=?',
            ('evm-gnosis-2',),
        )
        second_identifier = write_cursor.fetchone()[0]
        write_cursor.execute(
            'INSERT INTO chain_events_info(identifier, tx_ref, counterparty) VALUES (?, ?, ?)',
            (second_identifier, second_tx_hash, CPT_GNOSIS_PAY),
        )

    with patch.object(
            gnosispay_decoder.gnosispay_api,
            'update_events',
    ) as update_mock:
        gnosispay_decoder.gnosispay_api.backfill_missing_events()

    update_mock.assert_called_once_with(tx_timestamps={tx_hash: ts_ms_to_sec(timestamp_ms)})
    with gnosis_inquirer.database.conn.read_ctx() as cursor:
        cursor.execute('SELECT notes FROM history_events WHERE identifier=?', (second_identifier,))
        assert cursor.fetchone()[0] == second_note
