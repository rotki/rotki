from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.base.modules.basenames.constants import (
    BASENAMES_L2_RESOLVER,
    BASENAMES_REGISTRAR_CONTROLLER,
    BASENAMES_REGISTRY,
    CPT_BASENAMES,
)
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, Timestamp, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.base.node_inquirer import BaseInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_basenames_register(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x20280b43dbcfa86cdf0703d2e9f8f2ef200839b2ee0e819d895515d3adb74eff')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, gas_amount, token_id = TimestampMS(1726738619000), base_accounts[0], '0.000001963384627852', 26612040215479394739615825115912800930061094786769410446114278812336794170041  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=182,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Transfer base.eth node ownership of subnode yabir.base.eth to {user_address}',
            counterparty=CPT_BASENAMES,
            address=BASENAMES_REGISTRY,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=183,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Set Basenames address for yabir.base.eth',
            counterparty=CPT_BASENAMES,
            address=BASENAMES_REGISTRAR_CONTROLLER,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=186,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Address for yabir.base.eth changed to {user_address}',
            counterparty=CPT_BASENAMES,
            address=BASENAMES_L2_RESOLVER,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=189,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Transfer reverse node ownership of subnode with label hash 0x64030f995cc00663f6a687946a9f76ab209ed9e0adbcd79d483107cd9ab30cb0 to {user_address}',  # noqa: E501
            counterparty=CPT_BASENAMES,
            address=BASENAMES_REGISTRY,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=190,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Set Basenames address for yabir.base.eth',
            counterparty=CPT_BASENAMES,
            address=BASENAMES_REGISTRAR_CONTROLLER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=191,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.0009997724755728'),
            location_label=user_address,
            notes=f'Register Basenames name yabir.base.eth for 0.0009997724755728 ETH until {decoder.decoders["Basenames"].timestamp_to_date(Timestamp(1758296219))}',  # type: ignore[attr-defined]  # decoder will have date mixin  # noqa: E501
            counterparty=CPT_BASENAMES,
            address=BASENAMES_REGISTRAR_CONTROLLER,
            extra_data={'name': 'yabir.base.eth', 'expires': 1758296219},
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=192,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset(f'eip155:8453/erc721:0x03c4738Ee98aE44591e1A4A4F3CaB6641d95DD9a/{token_id}'),
            amount=ONE,
            location_label=user_address,
            notes=f'Receive Basenames name yabir.base.eth from {BASENAMES_REGISTRAR_CONTROLLER} to {user_address}',  # noqa: E501
            counterparty=CPT_BASENAMES,
            address=BASENAMES_REGISTRAR_CONTROLLER,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
def test_basenames_register_with_discount(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x9a7021f26ecabdd0d3a3781cec24a452851d97849defa9862a18230a9e72fbd9')  # noqa: E501
    events, decoder = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)  # noqa: E501
    timestamp, user_address, gas_amount, token_id = TimestampMS(1730993703000), base_accounts[0], '0.000005269375874545', 7069226722341729763252382492637378743849472286311622838562285205711946962668  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=402,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Transfer base.eth node ownership of subnode javxq.base.eth to {user_address}',
            counterparty=CPT_BASENAMES,
            address=BASENAMES_REGISTRY,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=403,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Set Basenames address for javxq.base.eth',
            counterparty=CPT_BASENAMES,
            address=BASENAMES_REGISTRAR_CONTROLLER,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=406,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Address for javxq.base.eth changed to {user_address}',
            counterparty=CPT_BASENAMES,
            address=BASENAMES_L2_RESOLVER,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=409,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Transfer reverse node ownership of subnode with label hash 0x1e5d04a39c97ae670c4612c7f1265a2839673d4f867820dab534e27d47d29e13 to {user_address}',  # noqa: E501
            counterparty=CPT_BASENAMES,
            address=BASENAMES_REGISTRY,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=410,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Set Basenames address for javxq.base.eth',
            counterparty=CPT_BASENAMES,
            address=BASENAMES_REGISTRAR_CONTROLLER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=411,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Register Basenames name javxq.base.eth until {decoder.decoders["Basenames"].timestamp_to_date(Timestamp(1762551303))}',  # type: ignore[attr-defined]  # decoder will have date mixin  # noqa: E501
            counterparty=CPT_BASENAMES,
            address=BASENAMES_REGISTRAR_CONTROLLER,
            extra_data={'name': 'javxq.base.eth', 'expires': 1762551303},
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=412,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset(f'eip155:8453/erc721:0x03c4738Ee98aE44591e1A4A4F3CaB6641d95DD9a/{token_id}'),
            amount=ONE,
            location_label=user_address,
            notes=f'Receive Basenames name javxq.base.eth from {BASENAMES_REGISTRAR_CONTROLLER} to {user_address}',  # noqa: E501
            counterparty=CPT_BASENAMES,
            address=BASENAMES_REGISTRAR_CONTROLLER,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x706A70067BE19BdadBea3600Db0626859Ff25D74']])
def test_basenames_set_attribute(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xb46d5e9cedf468d6c1cd9c5a07f7147448cfd5a0d591b6f57a8216edc2475cc4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount = TimestampMS(1730993863000), base_accounts[0], '0.000000860174471941'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=444,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Set Basenames com.twitter to jav_xq attribute for javxq.base.eth',
            counterparty=CPT_BASENAMES,
            address=BASENAMES_L2_RESOLVER,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x1208a26FAa0F4AC65B42098419EB4dAA5e580AC6']])
def test_basenames_content_hash_changed(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x1803ee8ecced1de613a331de58d7091e9fa0f4f98ec78bb9882b20b27b357aa7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount = TimestampMS(1725571165000), base_accounts[0], '0.000000178301347708'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=341,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Change Basenames content hash to ipfs://QmSVfQ1GYNmab2BnnvRFixAxENesPqre7DTkfKSafWcPnx for records.base.eth',  # noqa: E501
            counterparty=CPT_BASENAMES,
            address=BASENAMES_L2_RESOLVER,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize(('action', 'base_accounts'), [
    ('Transfer', ['0x2B97eb170a57fa2B5ea499b9f0176Ef587c6F54d', '0x6722d0fED54f02C60e9Cb6948aA18130eAc627c7']),  # noqa: E501
    ('Send', ['0x2B97eb170a57fa2B5ea499b9f0176Ef587c6F54d']),
    ('Receive', ['0x6722d0fED54f02C60e9Cb6948aA18130eAc627c7']),
])
def test_basenames_transfer_name(database, base_inquirer, action, base_accounts, add_subgraph_api_key):  # pylint: disable=unused-argument  # noqa: E501
    """Test that transferring a Basename name is decoded properly for all 3 cases.

    Owning both addresses in the transfer, only sender or only receiver
    """
    tx_hash = deserialize_evm_tx_hash('0x416c8a05f1fd8f780cb27e10c74327da31f201d1afc9fb9de620d17440b7343a')  # noqa: E501

    sequence_index = 228
    if action == 'Transfer':
        from_address = base_accounts[0]
        to_address = base_accounts[1]
        event_type = HistoryEventType.TRANSFER
        notes = f'Transfer Basenames name xardian.base.eth to {to_address}'
    elif action == 'Send':
        from_address = base_accounts[0]
        to_address = '0x6722d0fED54f02C60e9Cb6948aA18130eAc627c7'
        event_type = HistoryEventType.SPEND
        notes = f'Send Basenames name xardian.base.eth to {to_address}'
    else:  # Receive
        sequence_index = 227
        from_address = '0x2B97eb170a57fa2B5ea499b9f0176Ef587c6F54d'
        to_address = '0x6722d0fED54f02C60e9Cb6948aA18130eAc627c7'
        event_type = HistoryEventType.RECEIVE
        notes = f'Receive Basenames name xardian.base.eth from {from_address} to {to_address}'
        # For the event's location_label and address, when receiving swap them
        from_address = '0x6722d0fED54f02C60e9Cb6948aA18130eAc627c7'
        to_address = '0x2B97eb170a57fa2B5ea499b9f0176Ef587c6F54d'

    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp, token_id = TimestampMS(1731055033000), 112426549028048856546593988202926666418642845280196262619695088491431122056723  # noqa: E501
    gas_event = EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal('0.000000343395372337'),
        location_label=from_address,
        notes='Burn 0.000000343395372337 ETH for gas',
        counterparty=CPT_GAS,
        address=None,
    )
    expected_events = []
    if action != 'Receive':
        expected_events.append(gas_event)
    expected_events.append(EvmEvent(
        tx_hash=tx_hash,
        sequence_index=sequence_index,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=event_type,
        event_subtype=HistoryEventSubType.NONE,
        asset=Asset(f'eip155:8453/erc721:0x03c4738Ee98aE44591e1A4A4F3CaB6641d95DD9a/{token_id}'),
        amount=ONE,
        location_label=from_address,
        notes=notes,
        counterparty=CPT_BASENAMES,
        address=string_to_evm_address(to_address),
    ))
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x5C68b865B73271A9A1a3ee3792d396DacDe85702']])
def test_basenames_new_owner(
        base_inquirer: 'BaseInquirer',
        base_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x9c107455c41ac041b274d0c9f4a792e2cdccf3fb3abd31a117fb14570461b429')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp, user_address, gas_amount = TimestampMS(1730924307000), base_accounts[0], '0.000001274267527917'  # noqa: E501
    assert events == [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=294,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Transfer abdulla2918.base.eth node ownership of subnode with label hash 0xfa1ea47215815692a5f1391cff19abbaf694c82fb2151a4c351b6c0eeaaf317b to {user_address}',  # noqa: E501
            counterparty=CPT_BASENAMES,
            address=BASENAMES_REGISTRY,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=295,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Set Basenames address for an ENS name',
            counterparty=CPT_BASENAMES,
            address=BASENAMES_REGISTRY,
        ),
    ]
