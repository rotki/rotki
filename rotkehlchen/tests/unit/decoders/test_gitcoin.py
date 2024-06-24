import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.modules.gitcoin.constants import (
    GITCOIN_GC15_MATCHING,
    GITCOIN_GOVERNOR_ALPHA,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS, CPT_GITCOIN
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ZERO
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_POLYGON_POS_MATIC, A_SAI
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_gitcoin_old_donation(database, ethereum_inquirer):
    tx_hash = deserialize_evm_tx_hash('0x811ba23a10c76111289133ec6f90d3c33a604baa50053739210e870687a456d9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, gas = TimestampMS(1569924574000), '0.000055118'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas)),
            location_label=ADDY,
            notes=f'Burned {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=164,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.DONATE,
            asset=A_SAI,
            balance=Balance(amount=FVal('0.95'), usd_value=ZERO),
            location_label=ADDY,
            notes='Donate 0.95 SAI to 0xEbDb626C95a25f4e304336b1adcAd0521a1Bdca1 via gitcoin',
            counterparty=CPT_GITCOIN,
            address=string_to_evm_address('0xEbDb626C95a25f4e304336b1adcAd0521a1Bdca1'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=165,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.DONATE,
            asset=A_SAI,
            balance=Balance(amount=FVal('0.05'), usd_value=ZERO),
            location_label=ADDY,
            notes='Donate 0.05 SAI to 0x00De4B13153673BCAE2616b67bf822500d325Fc3 via gitcoin',
            counterparty=CPT_GITCOIN,
            address=string_to_evm_address('0x00De4B13153673BCAE2616b67bf822500d325Fc3'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_bulkcheckout_receive_eth(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6ed7d6c156fa3a8e73c3726d9179f139abcf7e7d3845efe9c5b70e6b4222c0be')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, user_address, amount, donor = TimestampMS(1670831003000), ethereum_accounts[0], '0.000799', '0xC8CA7F1C1a391CAfE43cf7348a2E54930648a0D4'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.DONATE,
        asset=A_ETH,
        balance=Balance(amount=FVal(amount)),
        location_label=user_address,
        notes=f'Receive donation of {amount} ETH from {donor} via gitcoin',
        counterparty=CPT_GITCOIN,
        address=donor,
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x81facc69908D9C1188280fBB2793567De39f8f9B']])
def test_bulkcheckout_send_token(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x89f8f62f7b1a8af0f8de685b676dac94088833442db93a9c4d896817b9f5099d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, gas, user_address, amount1, amount2, dst1, dst2 = TimestampMS(1671869867000), '0.000883451092980928', ethereum_accounts[0], '25', '1.25', '0x3A5bd1E37b099aE3386D13947b6a90d97675e5e3', '0xde21F729137C5Af1b01d73aF1dC21eFfa2B8a0d6'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas)),
            location_label=user_address,
            notes=f'Burned {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=38,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.DONATE,
            asset=A_DAI,
            balance=Balance(amount=FVal(amount1)),
            location_label=user_address,
            notes=f'Donate {amount1} DAI to {dst1} via gitcoin',
            counterparty=CPT_GITCOIN,
            address=dst1,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=40,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.DONATE,
            asset=A_DAI,
            balance=Balance(amount=FVal(amount2)),
            location_label=user_address,
            notes=f'Donate {amount2} DAI to {dst2} via gitcoin',
            counterparty=CPT_GITCOIN,
            address=dst2,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_polygon_bulkcheckout_receive_matic(database, polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash('0xe2d9464020f45ea2a69c93156976c1323a16e390550e0fe9af749e88e234e06b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, user_address, amount, donor = TimestampMS(1667285686000), polygon_pos_accounts[0], '2', '0x6e08E6e2D0deeb294fd53e9708f53b0fBedc06d5'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.DONATE,
        asset=A_POLYGON_POS_MATIC,
        balance=Balance(amount=FVal(amount)),
        location_label=user_address,
        notes=f'Receive donation of {amount} MATIC from {donor} via gitcoin',
        counterparty=CPT_GITCOIN,
        address=donor,
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_gitcoin_vote_cast(database, ethereum_inquirer):
    """Test the old vote cast that gitcoin governor has"""
    tx_hash = deserialize_evm_tx_hash('0x068a954e8c8eda8942e972977d252997bd9de766c7b59230377ebdb9351e0183')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, gas = TimestampMS(1659375478000), '0.001115205340736039'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas)),
            location_label=ADDY,
            notes=f'Burned {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=159,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.GOVERNANCE,
            asset=A_ETH,
            balance=Balance(),
            location_label=ADDY,
            notes='Voted FOR gitcoin governance proposal https://www.tally.xyz/gov/gitcoin/proposal/31',
            counterparty=CPT_GITCOIN,
            address=GITCOIN_GOVERNOR_ALPHA,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xB1b3751834646fb999EDd18CA62C69663071cF43']])
def test_gitcoin_gr15_matching_claim(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc7ba01598f7fee42bb3923af95355d676ad38ec0aebdcdf49eaf7cb74d2150b2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, gas, user, amount = TimestampMS(1666139015000), '0.00118573107792279', ethereum_accounts[0], '1719.1187865411025'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas)),
            location_label=user,
            notes=f'Burned {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=83,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.DONATE,
            asset=A_DAI,
            balance=Balance(FVal(amount)),
            location_label=user,
            notes=f'Claim {amount} DAI as matching funds payout for gitcoin round 15',
            counterparty=CPT_GITCOIN,
            address=GITCOIN_GC15_MATCHING,
        ),
    ]
    assert events == expected_events
