import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.modules.defisaver.constants import (
    CPT_DEFISAVER,
    FL_ACTION_V1_0_3,
    FL_ACTION_V1_0_3_BIS,
    SUB_STORAGE,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.safe.constants import CPT_SAFE_MULTISIG
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_WETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd312551890858CC313Bf1718F502FF9fcDB2e6ff']])
def test_subscribe(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x6c9e1aac8818eb5d40761f8c65041a227aec8d4d140b7e1684be80259b0f2138')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hex,
    )
    user_address, timestamp, gas = ethereum_accounts[0], TimestampMS(1676641271000), '0.02686452'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas)),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=304,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=user_address,
            notes='Subscribe to defisaver automation with subscription id 175 for proxy 0x81D1Eb6CAAE8C82999F1aeC30b095B54255e39f5',  # noqa: E501
            counterparty=CPT_DEFISAVER,
            address=SUB_STORAGE,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xd312551890858CC313Bf1718F502FF9fcDB2e6ff']])
def test_deactivate_sub(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x646352346021b3747143dfff704b6b61b736fd86479b5c1bdb0145c92e5d92a0')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hex,
    )
    user_address, timestamp, gas = ethereum_accounts[0], TimestampMS(1677329195000), '0.00099726'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(amount=FVal(gas)),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=74,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=user_address,
            notes='Deactivate defisaver automation subscription with id 175',
            counterparty=CPT_DEFISAVER,
            address=SUB_STORAGE,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xb4757065B2C5EEA193CC393bafF0D858987211FC']])
def test_defisaver_fl_action_v1_0_3(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x54b1df5ae9ea772d195c9f4fe182be12fd7989e1c7342d4bfd9539c68c1da0e0')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, flashloan_amount = TimestampMS(1713039743000), FVal('31.326004217665875683')
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=A_WETH.resolve_to_evm_token(),
            balance=Balance(amount=flashloan_amount),
            location_label=ethereum_accounts[0],
            notes=f'Executed flashloan of {flashloan_amount} WETH via DefiSaver',
            counterparty=CPT_DEFISAVER,
            address=FL_ACTION_V1_0_3,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=35,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=A_WETH.resolve_to_evm_token(),
            balance=Balance(amount=flashloan_amount),
            location_label=ethereum_accounts[0],
            notes=f'Repaid flashloan of {flashloan_amount} WETH via DefiSaver',
            counterparty=CPT_DEFISAVER,
            address=FL_ACTION_V1_0_3,
        ),
    ]
    assert set(expected_events).issubset(set(events))


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x72A559b0A41368ADC80Fbe77702a9A3CbB7C5156']])
def test_defisaver_fl_action_v1_0_3_bis(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xa3a8946f60d9718b4299dcc8aad0d9bc1340593300b630d70f3da21ca2f26893')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_safe_proxy, user_eoa_account, timestamp, flashloan_amount = ethereum_accounts[0], '0x07cB1b3a52Faf636A52822d918B07d30b0914d76', TimestampMS(1734679367000), FVal('140000')  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.NONE,
            asset=A_ETH,
            balance=Balance(),
            location_label=string_to_evm_address(user_eoa_account),
            notes=f'Successfully executed safe transaction 0xc513405c165b55b4dc27ef5735eea66e294d2bc25f09c10b71ad14ddd13c54c6 for multisig {user_safe_proxy}',  # noqa: E501
            counterparty=CPT_SAFE_MULTISIG,
            address=string_to_evm_address(user_safe_proxy),
        ),
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=375,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.GENERATE_DEBT,
            asset=EvmToken('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),  # crvUSD
            balance=Balance(amount=flashloan_amount),
            location_label=ethereum_accounts[0],
            notes=f'Executed flashloan of {flashloan_amount} crvUSD via DefiSaver',
            counterparty=CPT_DEFISAVER,
            address=FL_ACTION_V1_0_3_BIS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=400,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.PAYBACK_DEBT,
            asset=EvmToken('eip155:1/erc20:0xf939E0A03FB07F59A73314E73794Be0E57ac1b4E'),  # crvUSD
            balance=Balance(amount=flashloan_amount),
            location_label=ethereum_accounts[0],
            notes=f'Repaid flashloan of {flashloan_amount} crvUSD via DefiSaver',
            counterparty=CPT_DEFISAVER,
            address=FL_ACTION_V1_0_3_BIS,
        ),
    ]
    assert set(expected_events).issubset(set(events))
