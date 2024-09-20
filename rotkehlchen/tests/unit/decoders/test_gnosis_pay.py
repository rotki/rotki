from unittest.mock import patch

import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.gnosis.modules.gnosis_pay.constants import (
    CPT_GNOSIS_PAY,
    GNOSIS_PAY_CASHBACK_ADDRESS,
)
from rotkehlchen.constants.assets import Asset
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import (
    ApiKey,
    ExternalService,
    ExternalServiceApiCredentials,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)


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
            balance=Balance(amount=FVal(amount)),
            location_label=gnosis_accounts[0],
            notes=f'Receive cashback of {amount} GNO from Gnosis Pay',
            tx_hash=tx_hash,
            counterparty=CPT_GNOSIS_PAY,
            address=GNOSIS_PAY_CASHBACK_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [[
    '0xF4a1fB1689104479De1EcADfA472A9B866D08B16',  # user's gnosis pay safe
]])
def test_gnosis_pay_spend(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0xe8d666d6acf22e5a50dfea7ece1473558a854dfa04441ea9b3d0898843364ad8')  # noqa: E501
    events, gnosis_txs_decoder = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
    )
    gnosispay_decoder = gnosis_txs_decoder.decoders.get('GnosisPay')

    amount = '8.5'
    expected_events = [
        EvmEvent(
            sequence_index=29,
            timestamp=TimestampMS(1726590745000),
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYMENT,
            asset=Asset('eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430'),
            balance=Balance(amount=FVal(amount)),
            location_label=gnosis_accounts[0],
            notes=f'Spend {amount} EURe via Gnosis Pay',
            tx_hash=tx_hash,
            counterparty=CPT_GNOSIS_PAY,
            address='0x4822521E6135CD2599199c83Ea35179229A172EE',
        ),
    ]
    assert events == expected_events

    with gnosis_inquirer.database.user_write() as write_cursor:
        gnosis_inquirer.database.add_external_service_credentials(
            write_cursor=write_cursor,
            credentials=[ExternalServiceApiCredentials(service=ExternalService.GNOSIS_PAY, api_key=ApiKey('foo'))],  # noqa: E501
        )
    gnosispay_decoder.reload_data()

    def mock_gnosispay_api(url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, """[{
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
        }]""")

    with patch.object(
            gnosis_txs_decoder,  # do not reload data since this overwrites the api object
            'reload_data',
            lambda x: None,
    ), patch.object(
            gnosispay_decoder.gnosispay_api.session,  # mock api response
            'get',
            wraps=mock_gnosispay_api,
    ):
        events = gnosis_txs_decoder.decode_and_get_transaction_hashes(ignore_cache=True, tx_hashes=[tx_hash])  # noqa: E501
        expected_events[0].notes = 'Pay 8.5 EUR to Lidl sagt Danke in Berlin :country:DE:'
        assert events == expected_events
