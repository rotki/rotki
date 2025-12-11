from collections import defaultdict
from collections.abc import Sequence
from http import HTTPStatus
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import requests
from eth_utils import to_checksum_address

from rotkehlchen.accounting.structures.balance import Balance, BalanceSheet
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.zksync_lite.structures import ZKSyncLiteTransaction, ZKSyncLiteTXType
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_GNO
from rotkehlchen.constants.misc import DEFAULT_BALANCE_LABEL, ONE, ZERO
from rotkehlchen.db.filtering import EvmEventFilterQuery
from rotkehlchen.db.history_events import DBHistoryEvents
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.api import (
    api_url_for,
    assert_error_response,
    assert_proper_response,
    assert_proper_sync_response_with_result,
    assert_simple_ok_response,
)
from rotkehlchen.tests.utils.factories import make_evm_address, make_evm_tx_hash
from rotkehlchen.types import (
    ChecksumEvmAddress,
    Location,
    Timestamp,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.api.server import APIServer


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('zksync_lite_accounts', [[make_evm_address(), make_evm_address()]])
def test_evmlike_transactions_refresh(
        rotkehlchen_api_server: 'APIServer',
        zksync_lite_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Just tests the api part of refreshing evmlike transactions. Since at the moment
    this only concerns zksynclite, actual data check is in
    integration/test_zksynclite.py::test_get_transactions"""
    now = ts_now()

    # Timestamps are optional args here since zksynclite doesn't use them
    def mock_fetch_transactions(
            address: 'ChecksumEvmAddress',
            start_ts: int = 0,
            end_ts: int = now,
    ) -> None:
        assert to_checksum_address(address)
        assert start_ts == 0
        assert end_ts >= now

    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    for json_args, expected_count in [
            ({'async_query': False}, 2),
            ({'async_query': False, 'accounts': [{'address': zksync_lite_accounts[0], 'blockchain': 'zksync_lite'}]}, 1),  # noqa: E501
            ({'async_query': False, 'accounts': [{'address': zksync_lite_accounts[0], 'blockchain': 'zksync_lite'}, {'address': zksync_lite_accounts[1], 'blockchain': 'zksync_lite'}]}, 2),  # noqa: E501
            ({'async_query': False, 'accounts': [{'address': zksync_lite_accounts[0]}, {'address': zksync_lite_accounts[1]}]}, 2),  # noqa: E501
    ]:
        with patch.object(
                rotki.chains_aggregator.zksync_lite,
                'fetch_transactions',
                wraps=mock_fetch_transactions,
        ) as tx_query:
            response = requests.post(
                api_url_for(
                    rotkehlchen_api_server,
                    'blockchaintransactionsresource',
                ), json=json_args,
            )
            assert_simple_ok_response(response)
            assert tx_query.call_count == expected_count


@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('zksync_lite_accounts', [[make_evm_address(), make_evm_address()]])
def test_evmlike_blockchain_balances(
        rotkehlchen_api_server: 'APIServer',
        zksync_lite_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Just tests the api part of refreshing evmlike transactions. Since at the moment
    this only concerns zksynclite, actual data check is in
    integration/test_zksynclite.py::test_balances"""
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen

    addy_0_balances = {
        A_ETH: Balance(amount=FVal(10), value=FVal(1000)),
        A_DAI: Balance(amount=FVal(100), value=FVal(100)),
    }
    addy_1_balances = {
        A_ETH: Balance(amount=FVal(5), value=FVal(500)),
        A_GNO: Balance(amount=FVal(50), value=FVal(25)),
    }

    def serialize_balances(value: dict[Asset, Balance]) -> dict[str, dict]:
        return {asset.identifier: {DEFAULT_BALANCE_LABEL: balance.serialize()} for asset, balance in value.items()}  # noqa: E501

    def mocked_get_balances(
            addresses: Sequence[ChecksumEvmAddress],
    ) -> dict[ChecksumEvmAddress, BalanceSheet]:
        return {
            addresses[0]: BalanceSheet(assets=defaultdict(lambda: defaultdict(Balance), (
                (k, defaultdict(Balance, {DEFAULT_BALANCE_LABEL: v}))
                for k, v in addy_0_balances.items()
            ))),
            addresses[1]: BalanceSheet(assets=defaultdict(lambda: defaultdict(Balance), (
                (k, defaultdict(Balance, {DEFAULT_BALANCE_LABEL: v}))
                for k, v in addy_1_balances.items()
            ))),
        }

    with patch.object(
            rotki.chains_aggregator.zksync_lite,
            'query_balances',
            wraps=mocked_get_balances,
    ) as balance_query:
        response = requests.get(
            api_url_for(
                rotkehlchen_api_server,
                'blockchainbalancesresource',
            ), json={'async_query': False},
        )
        result = assert_proper_sync_response_with_result(response)
        assert balance_query.call_count == 1
        assert result == {
            'per_account': {
                'zksync_lite': {
                    zksync_lite_accounts[0]: {
                        'assets': serialize_balances(addy_0_balances),
                        'liabilities': {},
                    },
                    zksync_lite_accounts[1]: {
                        'assets': serialize_balances(addy_1_balances),
                        'liabilities': {},
                    },
                },
            },
            'totals': {
                'assets': {
                    A_ETH.identifier: {DEFAULT_BALANCE_LABEL: (addy_0_balances[A_ETH] + addy_1_balances[A_ETH]).serialize()},  # noqa: E501
                    A_GNO.identifier: {DEFAULT_BALANCE_LABEL: addy_1_balances[A_GNO].serialize()},
                    A_DAI.identifier: {DEFAULT_BALANCE_LABEL: addy_0_balances[A_DAI].serialize()},
                },
                'liabilities': {},
            },
        }


@pytest.mark.parametrize('number_of_eth_accounts', [0])
def test_evmlike_add_accounts(rotkehlchen_api_server: 'APIServer') -> None:
    """We will just add some zksync lite addresses

    This is a really fast test and tests the existing api for evmlike addresses
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    addy_0, addy_1 = make_evm_address(), make_evm_address()
    non_checksummed, checksummed = '0xcb14d5c77270af1234f027f967518b8eb69a9dee', '0xcb14D5c77270Af1234F027f967518b8Eb69a9deE'  # noqa: E501
    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ZKSYNC_LITE',
    ))
    result = assert_proper_sync_response_with_result(response)
    assert result == []

    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ZKSYNC_LITE',
    ), json={'accounts': [{'address': addy_0}]})
    assert_proper_response(response)

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ZKSYNC_LITE',
    ))
    result = assert_proper_sync_response_with_result(response)
    assert result == [{'address': addy_0, 'label': None, 'tags': None}]
    assert rotki.chains_aggregator.accounts.zksync_lite == (addy_0,)

    response = requests.put(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ZKSYNC_LITE',
    ), json={'accounts': [{'address': addy_1, 'label': 'addy 1 label'}]})
    assert_proper_response(response)

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ZKSYNC_LITE',
    ))
    result = assert_proper_sync_response_with_result(response)
    assert {'address': addy_1, 'label': 'addy 1 label', 'tags': None} in result
    assert {'address': addy_0, 'label': None, 'tags': None} in result

    assert rotki.chains_aggregator.accounts.zksync_lite == (addy_0, addy_1)

    response = requests.delete(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ZKSYNC_LITE',
    ), json={'accounts': [addy_0]})
    assert_proper_response(response)
    assert rotki.chains_aggregator.accounts.zksync_lite == (addy_1,)

    response = requests.put(api_url_for(  # add non-checksummed evm address
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ZKSYNC_LITE',
    ), json={'accounts': [{'address': non_checksummed}]})
    result = assert_proper_sync_response_with_result(response)
    assert result == [checksummed]  # see it's returned/saved checksummed

    response = requests.get(api_url_for(
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ZKSYNC_LITE',
    ))
    result = assert_proper_sync_response_with_result(response)
    assert {'address': checksummed, 'label': None, 'tags': None} in result

    response = requests.delete(api_url_for(  # delete non-checksummed address
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ZKSYNC_LITE',
    ), json={'accounts': [non_checksummed]})
    assert_proper_response(response)  # see it's deleted
    assert rotki.chains_aggregator.accounts.zksync_lite == (addy_1,)


def compare_events_without_id(e1: dict, e2: dict) -> None:
    e1.pop('identifier')
    e2.pop('identifier')
    assert e1 == e2


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('should_mock_price_queries', [True])
@pytest.mark.parametrize('default_mock_price_value', [ONE])
@pytest.mark.parametrize('number_of_eth_accounts', [0])
@pytest.mark.parametrize('zksync_lite_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_decode_pending_evmlike(
        rotkehlchen_api_server: 'APIServer',
        zksync_lite_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Tests pulling and decoding evmlike (zksync lite) transactions

    Also checks:
    - Redecoding a specific transaction for evmlike works
    - removing an account clears the DB properly
    """
    tx_hash1 = deserialize_evm_tx_hash('0xbd723b5a5f87e485a478bc7d1f365db79440b6e9305bff3b16a0e0ab83e51970')  # noqa: E501
    tx_hash2 = deserialize_evm_tx_hash('0x331fcc49dc3c0a772e0b5e4518350f3d9a5c5576b4e8dbc7c56b2c59caa239bb')  # noqa: E501
    user_address = zksync_lite_accounts[0]
    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'blockchaintransactionsresource',
        ), json={'async_query': False},
    )
    assert_simple_ok_response(response)

    response = requests.get(  # get the number of decoded & undecoded transactions
        api_url_for(
            rotkehlchen_api_server,
            'transactionsdecodingresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == {'zksync_lite': {'undecoded': 16, 'total': 16}}

    response = requests.post(
        api_url_for(
            rotkehlchen_api_server,
            'transactionsdecodingresource',
        ), json={'async_query': False, 'chain': 'zksync_lite'},
    )
    assert_proper_response(response)

    response = requests.get(  # get the number of decoded & undecoded transactions
        api_url_for(
            rotkehlchen_api_server,
            'transactionsdecodingresource',
        ),
    )
    result = assert_proper_sync_response_with_result(response)
    assert result == {}

    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
    )
    assert_proper_response(response)
    result = assert_proper_sync_response_with_result(response)
    response = requests.post(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json={'location': Location.ZKSYNC_LITE.serialize()},
    )
    assert assert_proper_sync_response_with_result(response) == result, 'filtering by location should be same'  # noqa: E501
    assert len(result['entries']) == 17
    compare_events_without_id(result['entries'][0]['entry'], EvmEvent(
        group_identifier='zkl0xbd723b5a5f87e485a478bc7d1f365db79440b6e9305bff3b16a0e0ab83e51970',
        tx_ref=tx_hash1,
        sequence_index=0,
        timestamp=TimestampMS(1708431030000),
        location=Location.ZKSYNC_LITE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=A_ETH,
        amount=FVal('6.626770825'),
        location_label=user_address,
        address=user_address,
        notes='Bridge 6.626770825 ETH from ZKSync Lite to Ethereum',
    ).serialize())
    compare_events_without_id(result['entries'][1]['entry'], EvmEvent(
        group_identifier='zkl0xbd723b5a5f87e485a478bc7d1f365db79440b6e9305bff3b16a0e0ab83e51970',
        tx_ref=tx_hash1,
        sequence_index=1,
        timestamp=TimestampMS(1708431030000),
        location=Location.ZKSYNC_LITE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.00367'),
        location_label=user_address,
        address=user_address,
        notes='Bridging fee of 0.00367 ETH',
    ).serialize())
    compare_events_without_id(result['entries'][2]['entry'], EvmEvent(
        group_identifier='zkl0x331fcc49dc3c0a772e0b5e4518350f3d9a5c5576b4e8dbc7c56b2c59caa239bb',
        tx_ref=tx_hash2,
        sequence_index=0,
        timestamp=TimestampMS(1659010582000),
        location=Location.ZKSYNC_LITE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=FVal('0.9630671085'),
        location_label=user_address,
        address=string_to_evm_address('0x9531C059098e3d194fF87FebB587aB07B30B1306'),
        notes='Receive 0.9630671085 ETH from 0x9531C059098e3d194fF87FebB587aB07B30B1306',
    ).serialize())

    # Now some events in same timestamp which can come at any order between 4-9 indices
    # It's multiple "batched" transfers, a ChangePubkey event and the fee at the end
    # with a 0 transfer to self
    for x in result['entries'][4:10]:  # normal transfer part of the batch
        if x['entry']['tx_ref'] == '0x43e7f5d480b8b7af4c154065fe7112b908940be39dd02f4fb42f6594d12465b7':  # noqa: E501
            compare_events_without_id(x['entry'], EvmEvent(
                group_identifier='zkl0x43e7f5d480b8b7af4c154065fe7112b908940be39dd02f4fb42f6594d12465b7',
                tx_ref=deserialize_evm_tx_hash('0x43e7f5d480b8b7af4c154065fe7112b908940be39dd02f4fb42f6594d12465b7'),
                sequence_index=0,
                timestamp=TimestampMS(1656022105000),
                location=Location.ZKSYNC_LITE,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=FVal('0.005'),
                location_label=user_address,
                address=string_to_evm_address('0xd31b671F1a398B519222FdAba5aB5464B9F2a3Fa'),
                notes='Send 0.005 ETH to 0xd31b671F1a398B519222FdAba5aB5464B9F2a3Fa',
            ).serialize())
            break
    else:
        raise AssertionError('Did not find the event')

    for x in result['entries'][4:10]:  # changepubkey
        if x['entry']['tx_ref'] == '0x83001f1c5580d90d345779cd10762fc71c4c9020202551bc480331d70d547cc7':  # noqa: E501
            compare_events_without_id(x['entry'], EvmEvent(
                group_identifier='zkl0x83001f1c5580d90d345779cd10762fc71c4c9020202551bc480331d70d547cc7',
                tx_ref=deserialize_evm_tx_hash('0x83001f1c5580d90d345779cd10762fc71c4c9020202551bc480331d70d547cc7'),
                sequence_index=0,
                timestamp=TimestampMS(1656022105000),
                location=Location.ZKSYNC_LITE,
                event_type=HistoryEventType.SPEND,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=FVal('0.001513'),
                location_label=user_address,
                notes='Spend 0.001513 ETH to ChangePubKey',
            ).serialize())
            break
    else:
        raise AssertionError('Did not find the event')

    for x in result['entries'][4:10]:  # fee by 0 transaction to self - transaction
        entry = x['entry']
        if entry['tx_ref'] == '0x89d943919cfa09636802e626c48cff7734da1ac8c98288c65fe5ea0dd60a0162' and entry['event_subtype'] == 'none':  # noqa: E501
            compare_events_without_id(entry, EvmEvent(
                group_identifier='zkl0x89d943919cfa09636802e626c48cff7734da1ac8c98288c65fe5ea0dd60a0162',
                tx_ref=deserialize_evm_tx_hash('0x89d943919cfa09636802e626c48cff7734da1ac8c98288c65fe5ea0dd60a0162'),
                sequence_index=0,
                timestamp=TimestampMS(1656022105000),
                location=Location.ZKSYNC_LITE,
                event_type=HistoryEventType.TRANSFER,
                event_subtype=HistoryEventSubType.NONE,
                asset=A_ETH,
                amount=ZERO,
                location_label=user_address,
                address=user_address,
                notes='Transfer 0 ETH to 0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12',
            ).serialize())
            break
    else:
        raise AssertionError('Did not find the event')

    for x in result['entries'][4:10]:  # fee by 0 transaction to self - fee
        entry = x['entry']
        if entry['tx_ref'] == '0x89d943919cfa09636802e626c48cff7734da1ac8c98288c65fe5ea0dd60a0162' and entry['event_subtype'] == 'fee':  # noqa: E501
            compare_events_without_id(entry, EvmEvent(
                group_identifier='zkl0x89d943919cfa09636802e626c48cff7734da1ac8c98288c65fe5ea0dd60a0162',
                tx_ref=deserialize_evm_tx_hash('0x89d943919cfa09636802e626c48cff7734da1ac8c98288c65fe5ea0dd60a0162'),
                sequence_index=1,
                timestamp=TimestampMS(1656022105000),
                location=Location.ZKSYNC_LITE,
                event_type=HistoryEventType.TRANSFER,
                event_subtype=HistoryEventSubType.FEE,
                asset=A_ETH,
                amount=FVal('0.0001843'),
                location_label=user_address,
                address=user_address,
                notes='Transfer fee of 0.0001843 ETH',
            ).serialize())
            break
    else:
        raise AssertionError('Did not find the event')

    # now let's try to redecode one transactions
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'transactionsdecodingresource'),
        json={'chain': 'zksync_lite', 'tx_refs': [str(tx_hash1)]},
    )
    assert_simple_ok_response(response)  # see all is fine

    # now let's check the DB contains the entries we will check against when deleting
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM zksynclite_transactions').fetchone()[0] == 16
        assert cursor.execute('SELECT COUNT(*) FROM zksynclite_swaps').fetchone()[0] == 0
        assert cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 17

    # now remove the address
    response = requests.delete(api_url_for(  # delete non-checksummed address
        rotkehlchen_api_server,
        'blockchainsaccountsresource',
        blockchain='ZKSYNC_LITE',
    ), json={'accounts': [user_address]})
    assert_proper_response(response)  # see it's deleted
    assert len(rotki.chains_aggregator.accounts.zksync_lite) == 0

    # finally check all related DB data got deleted
    with rotki.data.db.conn.read_ctx() as cursor:
        assert cursor.execute('SELECT COUNT(*) FROM zksynclite_transactions').fetchone()[0] == 0
        assert cursor.execute('SELECT COUNT(*) FROM zksynclite_swaps').fetchone()[0] == 0
        assert cursor.execute('SELECT COUNT(*) FROM history_events').fetchone()[0] == 0


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('zksync_lite_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_add_edit_evmlike_event(
        rotkehlchen_api_server: 'APIServer',
        zksync_lite_accounts: list['ChecksumEvmAddress'],
) -> None:
    """Test that adding and editing evmlike events works correctly and properly validates
    transaction hashes depending on if there is a corresponding transaction in the DB.
    """
    rotki = rotkehlchen_api_server.rest_api.rotkehlchen
    with rotki.data.db.conn.write_ctx() as write_cursor:
        rotki.chains_aggregator.zksync_lite._add_zksynctxs_db(
            write_cursor=write_cursor,
            transactions=[ZKSyncLiteTransaction(
                tx_hash=(tx_hash := make_evm_tx_hash()),
                tx_type=ZKSyncLiteTXType.TRANSFER,
                timestamp=Timestamp(1600000000),
                block_number=1,
                from_address=(user_address := zksync_lite_accounts[0]),
                to_address=make_evm_address(),
                asset=A_ETH,
                amount=ONE,
                fee=ONE,
                swap_data=None,
            )],
        )

    # Add an event with the existing tx hash
    entry = (event := EvmEvent(
        group_identifier='xyz',
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=TimestampMS(1600000000000),
        location=Location.ZKSYNC_LITE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.NONE,
        asset=A_ETH,
        amount=ONE,
        location_label=user_address,
        address=make_evm_address(),
    )).serialize()
    entry.pop('identifier')
    response = requests.put(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json=entry,
    )
    result = assert_proper_sync_response_with_result(response)
    entry['identifier'] = event.identifier = result['identifier']

    # Edit the event keeping the correct tx hash
    entry['user_notes'] = event.notes = 'test notes'
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json=entry,
    )
    assert_proper_sync_response_with_result(response)
    with rotki.data.db.conn.read_ctx() as cursor:
        assert DBHistoryEvents(rotki.data.db).get_history_events(
            cursor=cursor,
            filter_query=EvmEventFilterQuery.make(),
            entries_limit=None,
        ) == [event]

    # Try to edit with a tx hash that is not in the db or onchain
    entry['tx_ref'] = f'0x{"0" * 64}'  # don't use make_evm_tx_hash so this is always the same for the vcr.  # noqa: E501
    response = requests.patch(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json=entry,
    )
    assert_error_response(
        response=response,
        contained_in_msg='The provided transaction hash does not exist for zksync_lite.',
        status_code=HTTPStatus.BAD_REQUEST,
    )

    # Check that setting a real tx hash that's only missing from the DB pulls the tx from onchain.
    entry['tx_ref'] = '0x331fcc49dc3c0a772e0b5e4518350f3d9a5c5576b4e8dbc7c56b2c59caa239bb'
    assert_simple_ok_response(requests.patch(
        api_url_for(rotkehlchen_api_server, 'historyeventresource'),
        json=entry,
    ))
    with rotki.data.db.conn.read_ctx() as cursor:
        assert cursor.execute(
            'SELECT COUNT(*) FROM zksynclite_transactions WHERE tx_hash=?',
            (deserialize_evm_tx_hash(entry['tx_ref']),),
        ).fetchone()[0] == 1
