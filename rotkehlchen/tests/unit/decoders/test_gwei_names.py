from typing import Any

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.gwei_names.constants import CPT_GNS, GWEI_NAMES_ADDRESS
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, Timestamp, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_gwei_names_commit(ethereum_inquirer: Any, ethereum_accounts: Any) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x577fa8d03c70b168210bfd8e4582749b059b7a8ab092ccf558367262134bd61d')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1783181663000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.00000791364626367'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=575,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Commit to registering a GNS name',
            counterparty=CPT_GNS,
            address=GWEI_NAMES_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12']])
def test_gwei_names_register(ethereum_inquirer: Any, ethereum_accounts: Any) -> None:
    events, decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x8dbce5bb53b5a058ae38504202e025ddad273d24336014af2e10d9ed226e1b3b')),  # noqa: E501
    )
    expires_timestamp = Timestamp(1814717843)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1783181843000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.000022063022134344'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.0005'),
            location_label=user_address,
            notes=f'Register GNS name lefteris.gwei for 0.0005 ETH until {decoder.decoders["GweiNames"].timestamp_to_date(expires_timestamp)}',  # noqa: E501
            counterparty=CPT_GNS,
            address=GWEI_NAMES_ADDRESS,
            extra_data={'name': 'lefteris.gwei', 'expires': expires_timestamp},
        ), EvmSwapEvent(
            tx_ref=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset(f'eip155:1/erc721:{GWEI_NAMES_ADDRESS}/45991743056739617614238884298916192307526976321718109388251049935562689596137'),
            amount=ONE,
            location_label=user_address,
            notes=f'Receive GNS name lefteris.gwei from {ZERO_ADDRESS} to {user_address}',
            counterparty=CPT_GNS,
            address=GWEI_NAMES_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xf1B42cc7c1609445620dE4352CD7e58353C3FA74']])
def test_gwei_names_set_address(ethereum_inquirer: Any, ethereum_accounts: Any) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xe15a16eb6a93bae8a467776f5237ff2663d17741f89f580a3f03b639608d666f')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1783079603000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.00000977437994491'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=819,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes=f'Address for jim.gwei changed to {user_address}',
            counterparty=CPT_GNS,
            address=GWEI_NAMES_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xaB583a9E164CDd1B10e474a83DF3D0F2bdF99c95']])
def test_gwei_names_set_contenthash(ethereum_inquirer: Any, ethereum_accounts: Any) -> None:
    """Test that setting the contenthash (website) of a gwei name is decoded properly"""
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0xf8578c0f1cf825b103603d6ac219b1ad546924b1c000b179a01805442bded457')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1783072331000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.000031849482034734'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=392,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Change GNS content hash to ipfs://QmNveHHQQ3mh4pd6cM1zi2CPT31tcjEoYNswsR9AG7J1SA for k3tch4p.gwei',  # noqa: E501
            counterparty=CPT_GNS,
            address=GWEI_NAMES_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x20309Eb9080288e31AB1161366Af6639f04d593e']])
def test_gwei_names_set_text(ethereum_inquirer: Any, ethereum_accounts: Any) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x7e9ab5821256d0d152eaa199c475ae1a4dd16720a1dc28151d86dd78a69373f0')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1783180055000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.0000104263399416'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=2201,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Set GNS avatar to eip155:1/erc721:0x5af0d9827e0c53e4799bb226655a1de152a425a5/1243 attribute for skas.gwei',  # noqa: E501
            counterparty=CPT_GNS,
            address=GWEI_NAMES_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9398084E888CB5B5c126240439054b57C10138E7']])
def test_gwei_names_renew(ethereum_inquirer: Any, ethereum_accounts: Any) -> None:
    events, decoder = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x36d7e292fe72905d240399cd90728a2fae916fc11d29a8fdddfef78d3d4f5a9f')),  # noqa: E501
    )
    expires_timestamp = Timestamp(1846009919)
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1782937955000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.000007733653032468'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RENEW,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=FVal('0.0005'),
            location_label=user_address,
            notes=f'Renew GNS name aiiiden.gwei for 0.0005 ETH until {decoder.decoders["GweiNames"].timestamp_to_date(expires_timestamp)}',  # noqa: E501
            counterparty=CPT_GNS,
            address=GWEI_NAMES_ADDRESS,
            extra_data={'name': 'aiiiden.gwei', 'expires': expires_timestamp},
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xC04689227Fa24785609B1174698DBe481437f1A3']])
def test_gwei_names_set_primary_name(ethereum_inquirer: Any, ethereum_accounts: Any) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x14ad6f0582795bf40311d1f3c3666b6012a04c7a1690e97205b124df49ada82c')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1783067567000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.000007272510321351'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=249,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            amount=ZERO,
            location_label=user_address,
            notes='Set donnoh.gwei as GNS primary name',
            counterparty=CPT_GNS,
            address=GWEI_NAMES_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xf1B42cc7c1609445620dE4352CD7e58353C3FA74']])
def test_gwei_names_register_subdomain(ethereum_inquirer: Any, ethereum_accounts: Any) -> None:
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=(tx_hash := deserialize_evm_tx_hash('0x12d062afac37ed4a87615caeca1ac8d30a55a976506f057493e93a8f737ffba0')),  # noqa: E501
    )
    assert events == [
        EvmEvent(
            tx_ref=tx_hash,
            sequence_index=0,
            timestamp=(timestamp := TimestampMS(1783079675000)),
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str := '0.000021935730743095'),
            location_label=(user_address := ethereum_accounts[0]),
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_ref=tx_hash,
            sequence_index=1366,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.NONE,
            asset=Asset(f'eip155:1/erc721:{GWEI_NAMES_ADDRESS}/4173137658359921728993906935031819255455212706038239353816537143971616603592'),
            amount=ONE,
            location_label=user_address,
            notes='Register GNS subdomain jim.jim.gwei',
            counterparty=CPT_GNS,
            address=ZERO_ADDRESS,
        ),
    ]
