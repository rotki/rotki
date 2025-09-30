import pytest

from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.decoding.constants import CPT_GNOSIS_CHAIN
from rotkehlchen.chain.ethereum.modules.omnibridge.decoder import (
    BRIDGE_ADDRESS as ETHEREUM_BRIDGE_ADDRESS,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.gnosis.modules.omnibridge.decoder import (
    BRIDGE_ADDRESS as GNOSIS_BRIDGE_ADDRESS,
)
from rotkehlchen.constants.assets import A_ETH, A_GNO, A_USDT, A_XDAI, Asset
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xcA74F404E0C7bfA35B13B511097df966D5a65597']])
def test_omnibridge_ethereum_token_deposit(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x34b2058dd53b09c49fb415c402427f142d4da2789dff01655cc7254b949ec32d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, bridge_amount = ethereum_accounts[0], TimestampMS(1718409971000), '0.00097359584767956', '32.614964635297737403'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=2998,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_GNO,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} GNO from Ethereum to Gnosis via Gnosis Chain bridge',
            tx_hash=tx_hash,
            counterparty=CPT_GNOSIS_CHAIN,
            address=ETHEREUM_BRIDGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x683fC308f72491B33D200b4EB10Fa9780904173d']])
def test_omnibridge_ethereum_eth_deposit(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xa19b48afa68a21ed7076559f7f6234c25d11645ea757f0d66f960056dc263a67')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, bridge_amount = ethereum_accounts[0], TimestampMS(1723812767000), '0.000927846227501566', '0.4'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} WETH from Ethereum to Gnosis via Gnosis Chain bridge',
            tx_hash=tx_hash,
            counterparty=CPT_GNOSIS_CHAIN,
            address=string_to_evm_address('0xa6439Ca0FCbA1d0F80df0bE6A17220feD9c9038a'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xD2e5D774BE8dF6A2e5f091812e10149BbB12702f']])
def test_omnibridge_gnosis_token_deposit(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x36dfd776bcc430609ea47ea74893095f27e62e691d8622569cc43ea70cec3dd4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, bridge_amount = gnosis_accounts[0], TimestampMS(1723743095000), '0.000318556', '8416.007021'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} XDAI for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:100/erc20:0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83'),
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} USDC from Gnosis to Ethereum via Gnosis Chain bridge',
            tx_hash=tx_hash,
            counterparty=CPT_GNOSIS_CHAIN,
            address=GNOSIS_BRIDGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9164dDF23c029E30b2eB0EbacbB4dEa3C0E1ac43']])
def test_omnibridge_ethereum_token_withdrawal(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xa56d72db76b6c7cfd3db1d2d51902b6f611f5124157ae50a6fd2f5dac7bbfa54')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, bridge_amount = ethereum_accounts[0], TimestampMS(1723719059000), '0.000740577652951968', '8420.660675'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=415,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_USDT,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} USDT from Gnosis to Ethereum via Gnosis Chain bridge',
            tx_hash=tx_hash,
            counterparty=CPT_GNOSIS_CHAIN,
            address=ETHEREUM_BRIDGE_ADDRESS,
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x8D1D236F45a7DEcB769D88963b0F699cDBE5D833']])
def test_omnibridge_ethereum_eth_withdrawal(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x0d5b64cb8b79e4a728b22caf7ac51a0a595278fd6b2265775a4429a204e4e5e3')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, bridge_amount = ethereum_accounts[0], TimestampMS(1723786739000), '0.000333774965537772', '24.42848'  # noqa: E501
    assert events == [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=A_ETH,
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} WETH from Gnosis to Ethereum via Gnosis Chain bridge',
            tx_hash=tx_hash,
            counterparty=CPT_GNOSIS_CHAIN,
            address=string_to_evm_address('0xa6439Ca0FCbA1d0F80df0bE6A17220feD9c9038a'),
        ),
    ]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xcc2c6D82e00E14f81FFc8e4F6A26c4522adA5a34']])
def test_omnibridge_gnosis_token_withdrawal(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6d4006bc0927588758911407d0f01124056453ab8828897a1c4a125a5f574520')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=gnosis_inquirer, tx_hash=tx_hash)
    user_address, timestamp, bridge_amount = gnosis_accounts[0], TimestampMS(1598480695000), '300'
    assert events == [
        EvmEvent(
            sequence_index=4,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.BRIDGE,
            asset=Asset('eip155:100/erc20:0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83'),
            amount=FVal(bridge_amount),
            location_label=user_address,
            notes=f'Bridge {bridge_amount} USDC from Ethereum to Gnosis via Gnosis Chain bridge',
            tx_hash=tx_hash,
            counterparty=CPT_GNOSIS_CHAIN,
            address=ZERO_ADDRESS,
        ),
    ]
