from unittest.mock import patch

import gevent
import pytest
import requests

from rotkehlchen.api.server import APIServer
from rotkehlchen.chain.evm.decoding.monerium.constants import CPT_MONERIUM
from rotkehlchen.constants.assets import A_ETH_EURE
from rotkehlchen.constants.misc import ONE
from rotkehlchen.db.filtering import EvmEventFilterQuery, HistoryEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.externalapis.monerium import init_monerium
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import api_url_for, assert_proper_response
from rotkehlchen.tests.utils.mock import MockResponse
from rotkehlchen.types import ExternalService, Location, TimestampMS, deserialize_evm_tx_hash


def mock_monerium_and_run_periodic_task(database, contents):
    def mock_monerium(url, **kwargs):  # pylint: disable=unused-argument
        return MockResponse(200, contents)

    monerium = init_monerium(database)
    with gevent.Timeout(timeout := 4), patch('requests.Session.get', side_effect=mock_monerium):
        try:
            monerium.get_and_process_orders()
        except gevent.Timeout as e:
            raise AssertionError(f'monerium order query was not scheduled within {timeout} seconds') from e  # noqa: E501


def test_send_bank_transfer(database, monerium_credentials):  # pylint: disable=unused-argument
    """Test that sending a bank transfer on-chain via monerium is seen via their API
    and the periodic task identifies the event and properly annotates it"""
    dbevents = DBHistoryEvents(database)
    tx_hash = deserialize_evm_tx_hash(val='0x10d953610921f39d9d20722082077e03ec8db8d9c75e4b301d0d552119fd0354')  # noqa: E501
    amount_str = '1500'
    user_address = '0x99a0618B846D43E29C15ac468Eae06d03C9243C7'
    timestamp = TimestampMS(1701765059000)
    event = EvmEvent(
        tx_hash=tx_hash,
        sequence_index=171,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH_EURE,
        amount=FVal(amount_str),
        location_label=user_address,
        notes=f'Burn {amount_str} EURe',
        counterparty=CPT_MONERIUM,
    )
    with database.user_write() as write_cursor:
        dbevents.add_history_event(write_cursor=write_cursor, event=event)

    mock_monerium_and_run_periodic_task(
        database=database,
        contents='[{"id": "xx-yy", "profile": "zz-yy", "accountId": "aa-yy", "address": "0x99a0618B846D43E29C15ac468Eae06d03C9243C7", "kind": "redeem", "amount": "1500", "currency": "eur", "totalFee": "0", "fees": [], "counterpart": {"details": {"name": "Finanzamt Charlottenburg", "country": "DE", "companyName": "Finanzamt Charlottenburg"}, "identifier": {"iban": "DE94 1005 0000 6600 0464 63", "standard": "iban"}}, "memo": "LohnsteuerQ1", "supportingDocumentId": "", "chain": "ethereum", "network": "mainnet", "txHashes": ["0x10d953610921f39d9d20722082077e03ec8db8d9c75e4b301d0d552119fd0354"], "meta": {"state": "processed", "placedBy": "qq-yy", "placedAt": "2023-10-18T12:09:42.621469Z", "processedAt": "2023-10-18T12:09:43.621469Z", "approvedAt": "2023-10-18T12:09:44.621469Z", "confirmedAt": "2023-10-18T12:09:44.921469Z", "receivedAmount": "1500", "sentAmount": "1500"}}]',  # noqa: E501
    )

    # Set the expected changes in the event
    event.notes = 'Send 1500 EURe via bank transfer to Finanzamt Charlottenburg (DE94 1005 0000 6600 0464 63) with memo "LohnsteuerQ1"'  # noqa: E501
    event.identifier = 1
    with database.conn.read_ctx() as cursor:
        new_events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(
                tx_hashes=[tx_hash],
            ),
        )
    assert new_events == [event]


def test_receive_bank_transfer(database, monerium_credentials):  # pylint: disable=unused-argument
    """Test that receiving a bank transfer on-chain via monerium is seen via their API
    and the periodic task identifies the event and properly annotates it"""
    dbevents = DBHistoryEvents(database)
    tx_hash = deserialize_evm_tx_hash(val='0x4ed9db44c5ee4ba6a4cf3e8e9b386f0b857afebad8339a92666e175c747bdd74')  # noqa: E501
    amount_str = '1500'
    user_address = '0xbCCeE6Ff2bCAfA95300D222D316A29140c4746da'
    timestamp = TimestampMS(1701765059000)
    event = EvmEvent(
        tx_hash=tx_hash,
        sequence_index=113,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH_EURE,
        amount=FVal(amount_str),
        location_label=user_address,
        notes=f'Mint {amount_str} EURe',
        counterparty=CPT_MONERIUM,
    )
    with database.user_write() as write_cursor:
        dbevents.add_history_event(write_cursor=write_cursor, event=event)

    mock_monerium_and_run_periodic_task(
        database=database,
        contents='[{"id": "xx-yy", "profile": "zz-yy", "accountId": "aa-yy", "address": "0xbCCeE6Ff2bCAfA95300D222D316A29140c4746da", "kind": "issue", "amount": "1500", "currency": "eur", "totalFee": "0", "fees": [], "counterpart": {"details": {"name": "Payward Ltd", "country": "GB"}, "identifier": {"iban": "GB60 CLJU 0099 7129 9001 60", "standard": "iban"}}, "memo": "Kraken Tx AAA-BBB", "supportingDocumentId": "", "chain": "ethereum", "network": "mainnet", "txHashes": ["0x4ed9db44c5ee4ba6a4cf3e8e9b386f0b857afebad8339a92666e175c747bdd74"], "meta": {"state": "processed", "placedBy": "qq-yy", "placedAt": "2023-10-18T12:09:42.621469Z", "processedAt": "2023-10-18T12:09:43.621469Z", "approvedAt": "2023-10-18T12:09:44.621469Z", "confirmedAt": "2023-10-18T12:09:44.921469Z", "receivedAmount": "1500", "sentAmount": "1500"}}]',  # noqa: E501
    )

    # Set the expected changes in the event
    event.notes = 'Receive 1500 EURe via bank transfer from Payward Ltd (GB60 CLJU 0099 7129 9001 60) with memo "Kraken Tx AAA-BBB"'  # noqa: E501
    event.identifier = 1
    with database.conn.read_ctx() as cursor:
        new_events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(
                tx_hashes=[tx_hash],
            ),
        )
    assert new_events == [event]


def test_bridge_via_monerium(database, monerium_credentials):  # pylint: disable=unused-argument
    """Test that the case where the mint is a bridging from one chain to another is handled
    correctly and that the monerium API result is processed"""
    dbevents = DBHistoryEvents(database)
    ethhash = deserialize_evm_tx_hash(val='0x4ed9db44c5ee4ba6a4cf3e8e9b386f0b857afebad8339a92666e175c747bdd74')  # noqa: E501
    amount_str = '1500'
    gnosishash = deserialize_evm_tx_hash(val='0x10d953610921f39d9d20722082077e03ec8db8d9c75e4b301d0d552119fd0354')  # noqa: E501
    eth_user_address = '0x99a0618B846D43E29C15ac468Eae06d03C9243C7'
    gnosis_user_address = '0xbCCeE6Ff2bCAfA95300D222D316A29140c4746da'
    timestamp = TimestampMS(1701765059000)
    eth_event = EvmEvent(
        tx_hash=ethhash,
        sequence_index=171,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH_EURE,
        amount=FVal(amount_str),
        location_label=eth_user_address,
        notes=f'Burn {amount_str} EURe',
        counterparty=CPT_MONERIUM,
    )
    gnosis_event = EvmEvent(
        tx_hash=gnosishash,
        sequence_index=113,
        timestamp=timestamp,
        location=Location.GNOSIS,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH_EURE,
        amount=FVal(amount_str),
        location_label=gnosis_user_address,
        notes=f'Mint {amount_str} EURe',
        counterparty=CPT_MONERIUM,
    )
    with database.user_write() as write_cursor:
        dbevents.add_history_events(write_cursor=write_cursor, history=[eth_event, gnosis_event])

    mock_monerium_and_run_periodic_task(
        database=database,
        contents='[{"id": "xx-yy", "profile": "zz-yy", "accountId": "aa-yy", "address": "0xbCCeE6Ff2bCAfA95300D222D316A29140c4746da", "kind": "issue", "amount": "1500", "currency": "eur", "totalFee": "0", "fees": [], "counterpart": {"details": {}, "identifier": {"chain": "ethereum", "address": "0x99a0618B846D43E29C15ac468Eae06d03C9243C7", "network": "mainnet", "standard": "chain"}}, "memo": "Move to Gnosis Chain", "supportingDocumentId": "", "chain": "gnosis", "network": "mainnet", "txHashes": ["0x4ed9db44c5ee4ba6a4cf3e8e9b386f0b857afebad8339a92666e175c747bdd74", "0x10d953610921f39d9d20722082077e03ec8db8d9c75e4b301d0d552119fd0354"], "meta": {"state": "processed", "placedBy": "qq-yy", "placedAt": "2023-10-18T12:09:42.621469Z", "processedAt": "2023-10-18T12:09:43.621469Z", "approvedAt": "2023-10-18T12:09:44.621469Z", "confirmedAt": "2023-10-18T12:09:44.921469Z", "receivedAmount": "1500", "sentAmount": "1500"}},{"id": "pp-yy", "profile": "ll-yy", "accountId": "kk-yy", "address": "0x99a0618B846D43E29C15ac468Eae06d03C9243C7", "kind": "redeem", "amount": "1500", "currency": "eur", "totalFee": "0", "fees": [], "counterpart": {"details": {}, "identifier": {"chain": "gnosis", "address": "0xbCCeE6Ff2bCAfA95300D222D316A29140c4746da", "network": "mainnet", "standard": "chain"}}, "memo": "Move to Gnosis Chain", "supportingDocumentId": "", "chain": "ethereum", "network": "mainnet", "txHashes": ["0x4ed9db44c5ee4ba6a4cf3e8e9b386f0b857afebad8339a92666e175c747bdd74", "0x10d953610921f39d9d20722082077e03ec8db8d9c75e4b301d0d552119fd0354"], "meta": {"state": "processed", "placedBy": "qq-yy", "placedAt": "2023-10-18T12:09:42.621469Z", "processedAt": "2023-10-18T12:09:43.621469Z", "approvedAt": "2023-10-18T12:09:44.621469Z", "confirmedAt": "2023-10-18T12:09:44.921469Z", "receivedAmount": "1500", "sentAmount": "1500"}}]',  # noqa: E501
    )

    # Set the expected changes in the events
    eth_event.identifier = 1
    eth_event.notes = 'Bridge 1500 EURe to gnosis with memo "Move to Gnosis Chain"'
    eth_event.event_type = HistoryEventType.DEPOSIT
    eth_event.event_subtype = HistoryEventSubType.BRIDGE
    gnosis_event.identifier = 2
    gnosis_event.notes = 'Bridge 1500 EURe from ethereum with memo "Move to Gnosis Chain"'
    gnosis_event.event_type = HistoryEventType.WITHDRAWAL
    gnosis_event.event_subtype = HistoryEventSubType.BRIDGE
    with database.conn.read_ctx() as cursor:
        new_events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(
                counterparties=[CPT_MONERIUM],
            ),
        )
    assert new_events == [gnosis_event, eth_event]


@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('start_with_valid_premium', [True])
@pytest.mark.parametrize('have_decoders', [True])
def test_query_info_on_redecode_request(rotkehlchen_api_server: APIServer):
    """Test that triggering a re-decode for a monerium transaction updates correctly the notes"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    database = rotki.data.db
    # TODO: figure out why the fixture `start_with_valid_premium` doesn't activate the premium
    # by calling the chain aggregator
    rotki.chains_aggregator.activate_premium_status(rotki.premium)  # type: ignore
    dbevents = DBHistoryEvents(database)
    amount_str = '1500'
    gnosishash = deserialize_evm_tx_hash(val='0x10d953610921f39d9d20722082077e03ec8db8d9c75e4b301d0d552119fd0354')  # noqa: E501
    gnosis_user_address = '0xbCCeE6Ff2bCAfA95300D222D316A29140c4746da'
    gnosis_event = EvmEvent(
        tx_hash=gnosishash,
        sequence_index=113,
        timestamp=TimestampMS(1701765059000),
        location=Location.GNOSIS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH_EURE,
        amount=FVal(amount_str),
        location_label=gnosis_user_address,
        notes=f'Burn {amount_str} EURe',
        counterparty=CPT_MONERIUM,
    )
    with database.user_write() as write_cursor:
        write_cursor.execute(  # not using the fixture since it has issues with the api
            'INSERT OR REPLACE INTO external_service_credentials(name, api_key, api_secret) '
            'VALUES(?, ?, ?)',
            (ExternalService.MONERIUM.name.lower(), 'mockuser', 'mockpassword'),
        )

    def add_event(self, *args, **kwargs):  # pylint: disable=unused-argument
        with database.conn.read_ctx() as cursor:
            # reload data so the monerium decoder inits the api
            self.reload_data(cursor)

        with database.user_write() as write_cursor:
            dbevents.add_history_events(write_cursor=write_cursor, history=[gnosis_event])

        # call post process to add metadata into the decoded transaction
        self._post_process(refresh_balances=False, events=[gnosis_event])
        return [gnosis_event]

    response_txt = '[{"id":"YYYY","profile":"PP","accountId":"PP","address":"0xbCCeE6Ff2bCAfA95300D222D316A29140c4746da","kind":"redeem","amount":"2353.57","currency":"eur","totalFee":"0","fees":[],"counterpart":{"details":{"name":"Yabir Benchakhtir","country":"ES","lastName":"Benchakhtir","firstName":"Yabir"},"identifier":{"iban":"ESXX KKKK OOOO IIII KKKK LLLL","standard":"iban"}},"memo":"Venta inversion","supportingDocumentId":"","chain":"gnosis","network":"mainnet","txHashes":["0x10d953610921f39d9d20722082077e03ec8db8d9c75e4b301d0d552119fd0354"],"meta":{"state":"processed","placedBy":"ii","placedAt":"2024-04-19T13:45:00.287212Z","processedAt":"2024-04-19T13:45:00.287212Z","approvedAt":"2024-04-19T13:45:00.287212Z","confirmedAt":"2024-04-19T13:45:00.287212Z","receivedAmount":"2353.57","sentAmount":"2353.57"}}]'  # noqa: E501
    with (
        patch('requests.Session.get', side_effect=lambda *args, **kwargs: MockResponse(200, response_txt)),  # noqa: E501
        patch('rotkehlchen.chain.evm.decoding.decoder.EVMTransactionDecoder.decode_and_get_transaction_hashes', new=add_event),  # noqa: E501
        patch('rotkehlchen.chain.evm.transactions.EvmTransactions.get_or_query_transaction_receipt', return_value=None),  # noqa: E501
    ):
        response = requests.put(
            api_url_for(
                rotkehlchen_api_server,
                'evmtransactionsresource',
            ),
            json={'transactions': [{'evm_chain': 'gnosis', 'tx_hash': gnosishash.hex()}]},  # pylint: disable=no-member
        )
        assert_proper_response(response)

    with database.conn.read_ctx() as cursor:
        events = dbevents.get_history_events_internal(
            cursor=cursor,
            filter_query=HistoryEventFilterQuery.make(),
        )

    assert events[0].notes == 'Send 2353.57 EURe via bank transfer to Yabir Benchakhtir (ESXX KKKK OOOO IIII KKKK LLLL) with memo "Venta inversion"'  # noqa: E501
