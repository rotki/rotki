import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GNOSIS_CHAIN
from rotkehlchen.chain.ethereum.modules.xdai_bridge.decoder import BRIDGE_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.gnosis.modules.xdai_bridge.decoder import (
    BRIDGE_ADDRESS as GNOSIS_BRIDGE_ADDRESS,
)
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_XDAI
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x4c1a316De360E08817eB88dD31A0E7305005fB65']])
def test_bridge_dai_from_ethereum(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xe17f61edb9fe278720679ecfd5498f75082e38bf4779e5e6403a551f5084ee23')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
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
            balance=Balance(amount=FVal(0.000639911080514288)),
            location_label=user_address,
            notes='Burned 0.000639911080514288 ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=63,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_DAI,
            balance=Balance(amount=amount),
            location_label=user_address,
            notes=f'Bridge {amount} DAI from Ethereum to Gnosis via Gnosis Chain bridge',
            tx_hash=tx_hash,
            counterparty=CPT_GNOSIS_CHAIN,
            address=BRIDGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x07AD02e0C1FA0b09fC945ff197E18e9C256838c6']])
def test_withdraw_dai_to_ethereum(database, ethereum_inquirer, ethereum_accounts):
    user_address = ethereum_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0xb151a9294e7cdf9b62d5716eff3d69cc96c6fa3f1279b1d36c16896bd9cb3b32')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
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
            balance=Balance(amount=FVal(0.004855251)),
            location_label=user_address,
            notes='Burned 0.004855251 ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=171,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_DAI,
            balance=Balance(amount=amount),
            location_label=user_address,
            notes=f'Bridge {amount} DAI from Gnosis to Ethereum via Gnosis Chain bridge',
            tx_hash=tx_hash,
            counterparty=CPT_GNOSIS_CHAIN,
            address=BRIDGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr()
@pytest.mark.parametrize('gnosis_accounts', [['0x07AD02e0C1FA0b09fC945ff197E18e9C256838c6']])
def test_withdraw_dai_from_gnosis(database, gnosis_inquirer, gnosis_accounts):
    user_address = gnosis_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0x1a7014cbc1e6af2558c3a3cafd7fe87d8d67d27242b5abe8af0d4bf51a5230f6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
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
            balance=Balance(amount=FVal(0.0003624774)),
            location_label=user_address,
            notes='Burned 0.0003624774 XDAI for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_XDAI,
            balance=Balance(amount=amount),
            location_label=user_address,
            notes=f'Bridge {amount} XDAI from Gnosis to Ethereum via Gnosis Chain bridge',
            tx_hash=tx_hash,
            counterparty=CPT_GNOSIS_CHAIN,
            address=GNOSIS_BRIDGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr()
@pytest.mark.parametrize('gnosis_accounts', [['0x7DA9A33d15413F499299687cC9d81DE84684E28E']])
def test_deposit_dai_to_gnosis(database, gnosis_inquirer, gnosis_accounts):
    user_address = gnosis_accounts[0]
    tx_hash = deserialize_evm_tx_hash('0x5892a695860f6087a2d93140f05e6365142ff77fd7128e39dbc03128d5797ac4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    assert events == [EvmEvent(
        sequence_index=24,
        timestamp=TimestampMS(1609959945000),
        location=Location.GNOSIS,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.BRIDGE,
        asset=A_XDAI,
        balance=Balance(amount=FVal(20)),
        location_label=user_address,
        notes='Bridge 20 XDAI from Ethereum to Gnosis via Gnosis Chain bridge',
        tx_hash=tx_hash,
        counterparty=CPT_GNOSIS_CHAIN,
        address=GNOSIS_BRIDGE_ADDRESS,
    )]
