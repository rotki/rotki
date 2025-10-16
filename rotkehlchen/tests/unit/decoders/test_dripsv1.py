import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.drips.v1.constants import CPT_DRIPS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_project_collect_and_split(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xb116dfdef772f79ff7f28823cdb3f9f9eb61b8e774d038346d576f817572af0a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    gas, amount, timestamp = '0.0013334084', '1575.363922839504794511', TimestampMS(1660127734000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.DONATE,
            asset=A_DAI,
            amount=FVal(amount),
            location_label=ethereum_accounts[0],
            notes=f'Collect {amount} DAI from Drips v1 and forward 741.347728395061079769 DAI to dependencies for splitting',  # noqa: E501
            counterparty=CPT_DRIPS,
            address=string_to_evm_address('0x73043143e0A6418cc45d82D4505B096b802FD365'),
        ),
    ]
    assert events[:2] == expected_events
    assert len(events) == 10
    idx = 2
    for event, (amount, target) in zip(
            events[2:],
            [
                ('115.835582561728293714', '0x106B62Fdd27B748CF2Da3BacAB91a2CaBaeE6dCa'),
                ('115.835582561728293714', '0x19e4057A38a730be37c4DA690b103267AAE1d75d'),
                ('115.835582561728293714', '0x4bBa290826C253BD854121346c370a9886d1bC26'),
                ('115.835582561728293714', '0x5e4D630C35ef5c23ac57cF6bf8f2267D9E3CB78F'),
                ('115.835582561728293714', '0x7277F7849966426d345D8F6B9AFD1d3d89183083'),
                ('23.167116512345658742', '0x9d4E94dB689Bc471E45b0a18B7BdA36FcCeC9c3b'),
                ('115.835582561728293714', '0xc37b40ABdB939635068d3c5f13E7faF686F03B65'),
                ('23.167116512345658743', '0xf503017D7baF7FBC0fff7492b751025c6A78179b'),
            ], strict=False,
    ):
        assert event == EvmEvent(
            tx_hash=tx_hash,
            sequence_index=idx,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_DAI,
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes=f'Split {amount} DAI from Drips v1 and forward to {target}',
            counterparty=CPT_DRIPS,
            address=string_to_evm_address('0x73043143e0A6418cc45d82D4505B096b802FD365'),
        )
        idx += 1


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5e4D630C35ef5c23ac57cF6bf8f2267D9E3CB78F']])
def test_enduser_collect(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x38b957eaa21ba7a35c8713559680329f4b6b04bd46db00b54217c9d590c1a514')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    gas, amount, timestamp = '0.0003162699', '125.835582561728229714', TimestampMS(1660733511000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=421,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.DONATE,
            asset=A_DAI,
            amount=FVal(amount),
            location_label=ethereum_accounts[0],
            notes=f'Collect {amount} DAI from Drips v1',
            counterparty=CPT_DRIPS,
            address=string_to_evm_address('0x73043143e0A6418cc45d82D4505B096b802FD365'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_splits_updated(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2de9986920477923868559fc8b2a341972cb58c0824c46065d9ec2e11e4f9cad')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    gas, amount, timestamp = '0.00449242', '149.99999999999904', TimestampMS(1655506732000)
    assert events[0] == EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas} ETH for gas',
        counterparty=CPT_GAS,
    )

    for idx, sequence_index, (address, percent) in zip(
            range(1, 9),
            range(523, 530),
            [
                ('0x106B62Fdd27B748CF2Da3BacAB91a2CaBaeE6dCa', '5.00'),
                ('0x19e4057A38a730be37c4DA690b103267AAE1d75d', '5.00'),
                ('0x4bBa290826C253BD854121346c370a9886d1bC26', '5.00'),
                ('0x5e4D630C35ef5c23ac57cF6bf8f2267D9E3CB78F', '5.00'),
                ('0x7277F7849966426d345D8F6B9AFD1d3d89183083', '5.00'),
                ('0x9d4E94dB689Bc471E45b0a18B7BdA36FcCeC9c3b', '1.00'),
                ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '5.00'),
                ('0xf503017D7baF7FBC0fff7492b751025c6A78179b', '1.00'),
            ], strict=False,
    ):
        assert events[idx] == EvmEvent(
            tx_hash=tx_hash,
            sequence_index=sequence_index,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes=f'Setup Drips v1 rule to drip {percent}% of incoming drip funds to {address}',
            counterparty=CPT_DRIPS,
            address=string_to_evm_address('0x73043143e0A6418cc45d82D4505B096b802FD365'),
        )

        assert events[9] == EvmEvent(
            tx_hash=tx_hash,
            sequence_index=531,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.DONATE,
            asset=A_DAI,
            amount=FVal(amount),
            location_label=ethereum_accounts[0],
            notes=f'Collect {amount} DAI from Drips v1 and forward 49.99999999999968 DAI to dependencies for splitting',  # noqa: E501
            counterparty=CPT_DRIPS,
            address=string_to_evm_address('0x73043143e0A6418cc45d82D4505B096b802FD365'),
        )

    for idx, sequence_index, (address, amount) in zip(
            range(10, 19),
            range(532, 537),
            [
                ('0x106B62Fdd27B748CF2Da3BacAB91a2CaBaeE6dCa', '9.999999999999936'),
                ('0x5e4D630C35ef5c23ac57cF6bf8f2267D9E3CB78F', '9.999999999999936'),
                ('0x7277F7849966426d345D8F6B9AFD1d3d89183083', '9.999999999999936'),
                ('0x9d4E94dB689Bc471E45b0a18B7BdA36FcCeC9c3b', '3.9999999999999744'),
                ('0xc37b40ABdB939635068d3c5f13E7faF686F03B65', '9.999999999999936'),
                ('0xf503017D7baF7FBC0fff7492b751025c6A78179b', '5.9999999999999616'),
            ], strict=False,
    ):
        assert events[idx] == EvmEvent(
            tx_hash=tx_hash,
            sequence_index=sequence_index,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_DAI,
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes=f'Split {amount} DAI from Drips v1 and forward to {address}',
            counterparty=CPT_DRIPS,
            address=string_to_evm_address('0x73043143e0A6418cc45d82D4505B096b802FD365'),
        )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xbf55cd696C7D6dD9974Bec0de03162dCAEfA7c55']])
def test_give(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x104b65d6b29a133b6eb7950da6abed747c3a806356da5a351a94bbb73ca2271e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    gas, amount, timestamp = '0.001515204384196608', '1', TimestampMS(1660666663000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=688,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.DONATE,
            asset=A_DAI,
            amount=FVal(amount),
            location_label=ethereum_accounts[0],
            notes=f'Deposit {amount} DAI to Drips v1 as a donation for 0x308Fd8FB79379dEAD5A360FFb6Dd2D1AFf9F5EE4',  # noqa: E501
            counterparty=CPT_DRIPS,
            address=string_to_evm_address('0x73043143e0A6418cc45d82D4505B096b802FD365'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x1007A39088C22A4dfe54032F08fC47A7303603Df']])
def test_set_drips(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x86b8ea87f33cc6ac11286d229840e75f9328380f1b2b2c50ba93f173a97762dc')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)  # noqa: E501
    gas, amount, timestamp, per_sec_amount, end_ts = '0.005778677878564032', '50', TimestampMS(1654597232000), '0.000001929012345679', 1667557232  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.DONATE,
            asset=A_DAI,
            amount=FVal(amount),
            location_label=ethereum_accounts[0],
            notes=f'Deposit {amount} DAI to Drips v1 to start dripping donations',
            counterparty=CPT_DRIPS,
            address=string_to_evm_address('0x73043143e0A6418cc45d82D4505B096b802FD365'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes=f'Drip {per_sec_amount} DAI per second to 0xb8150a1B6945e75D05769D685b127b41E6335Bbc until {decoder.decoders["Dripsv1"].timestamp_to_date(end_ts)}',  # noqa: E501
            counterparty=CPT_DRIPS,
            address=string_to_evm_address('0x73043143e0A6418cc45d82D4505B096b802FD365'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes=f'Drip {per_sec_amount} DAI per second to 0xBABEEbC4f9dEbc9DA0ABf1Bbe5680554F8c97438 until {decoder.decoders["Dripsv1"].timestamp_to_date(end_ts)}',  # noqa: E501
            counterparty=CPT_DRIPS,
            address=string_to_evm_address('0x73043143e0A6418cc45d82D4505B096b802FD365'),
        ),
    ]
    assert events == expected_events
