from typing import TYPE_CHECKING

import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GNOSIS_CHAIN
from rotkehlchen.chain.ethereum.modules.xdai_bridge.decoder import (
    BRIDGE_ADDRESS,
    XDAI_BRIDGE_PERIPHERAL_PRE_USDS,
)
from rotkehlchen.chain.gnosis.modules.xdai_bridge.decoder import (
    BRIDGE_ADDRESS as GNOSIS_BRIDGE_ADDRESS,
)
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_XDAI
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.types import ChecksumEvmAddress


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x4c1a316De360E08817eB88dD31A0E7305005fB65']])
def test_bridge_dai_from_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xe17f61edb9fe278720679ecfd5498f75082e38bf4779e5e6403a551f5084ee23')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1697470703000)
    amount = FVal('19.997099097418611102')
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0.000639911080514288),
            location_label=user_address,
            notes='Burn 0.000639911080514288 ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=63,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_DAI,
            amount=amount,
            location_label=user_address,
            notes=f'Bridge {amount} DAI from Ethereum to Gnosis via Gnosis Chain bridge',
            tx_hash=tx_hash,
            counterparty=CPT_GNOSIS_CHAIN,
            address=BRIDGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_bridge_dai_from_ethereum_pre_usds_upgrade(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0x220b7397ce4b2f03b6871eb57762396aa0140d57dac4623d241e5eb02a0bc349')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1750340699000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000401361155268309'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        tx_hash=tx_hash,
        counterparty=CPT_GAS,
    ), EvmEvent(
        sequence_index=446,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=A_DAI,
        amount=FVal(bridge_amount := '569.981290146184006921'),
        location_label=user_address,
        notes=f'Bridge {bridge_amount} DAI from Ethereum to Gnosis via Gnosis Chain bridge',
        tx_hash=tx_hash,
        counterparty=CPT_GNOSIS_CHAIN,
        address=XDAI_BRIDGE_PERIPHERAL_PRE_USDS,
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xfF025244b556F0CD4617FBfE67F7986D7292A3E4']])
def test_bridge_dai_from_ethereum_nolog(ethereum_inquirer, ethereum_accounts):
    """Test the case where a simple transfer to the bridge is recognized as a bridging event"""
    tx_hash = deserialize_evm_tx_hash('0x196e7d687e1e2ce280dbe7f52b6ffe5a61d3a851b38740a37d1d00caffce7562')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1705093391000)
    gas, amount = '0.00115669008897503', '193.961036565990280733'
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=150,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_DAI,
            amount=FVal(amount),
            location_label=user_address,
            notes=f'Bridge {amount} DAI from Ethereum to Gnosis via Gnosis Chain bridge',
            tx_hash=tx_hash,
            counterparty=CPT_GNOSIS_CHAIN,
            address=BRIDGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x07AD02e0C1FA0b09fC945ff197E18e9C256838c6']])
def test_withdraw_dai_to_ethereum(ethereum_inquirer, ethereum_accounts):
    user_address = ethereum_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0xb151a9294e7cdf9b62d5716eff3d69cc96c6fa3f1279b1d36c16896bd9cb3b32')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1697473655000)
    amount = FVal(900)
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(0.004855251),
            location_label=user_address,
            notes='Burn 0.004855251 ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=171,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_DAI,
            amount=amount,
            location_label=user_address,
            notes=f'Bridge {amount} DAI from Gnosis to Ethereum via Gnosis Chain bridge',
            tx_hash=tx_hash,
            counterparty=CPT_GNOSIS_CHAIN,
            address=BRIDGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('gnosis_accounts', [['0x07AD02e0C1FA0b09fC945ff197E18e9C256838c6']])
def test_withdraw_dai_from_gnosis(gnosis_inquirer, gnosis_accounts):
    user_address = gnosis_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0x1a7014cbc1e6af2558c3a3cafd7fe87d8d67d27242b5abe8af0d4bf51a5230f6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1697473395000)
    amount = FVal(900)
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(0.0003624774),
            location_label=user_address,
            notes='Burn 0.0003624774 XDAI for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_XDAI,
            amount=amount,
            location_label=user_address,
            notes=f'Bridge {amount} XDAI from Gnosis to Ethereum via Gnosis Chain bridge',
            tx_hash=tx_hash,
            counterparty=CPT_GNOSIS_CHAIN,
            address=GNOSIS_BRIDGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr
@pytest.mark.parametrize('gnosis_accounts', [['0x7DA9A33d15413F499299687cC9d81DE84684E28E']])
def test_deposit_dai_to_gnosis(gnosis_inquirer, gnosis_accounts):
    user_address = gnosis_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0x5892a695860f6087a2d93140f05e6365142ff77fd7128e39dbc03128d5797ac4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        sequence_index=24,
        timestamp=TimestampMS(1609959945000),
        location=Location.GNOSIS,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=A_XDAI,
        amount=FVal(20),
        location_label=user_address,
        notes='Bridge 20 XDAI from Ethereum to Gnosis via Gnosis Chain bridge',
        tx_hash=tx_hash,
        counterparty=CPT_GNOSIS_CHAIN,
        address=GNOSIS_BRIDGE_ADDRESS,
    )]
