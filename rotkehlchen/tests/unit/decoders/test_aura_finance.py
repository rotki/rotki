import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.aura_finance.constants import CPT_AURA_FINANCE
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x6DF95c1F5AdD9cE98a013AD9809782d10272c6b8']])
def test_aura_finance_deposit_arb(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x9c3b996891eb0ffb5261486ff77c69c20a332499b9cf4196df7fab2c2123ea5f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp, gas_str, deposit_amount, receive_amount, approve_amount = arbitrum_one_accounts[0], TimestampMS(1732504225000), '0.00000372964', '2.862546191448752712', '2.054508357973208982', '115792089237316195423570985008687907853269984665640564039448.345378216051229581'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(gas_str)),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=4,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:42161/erc20:0x223738a747383d6F9f827d95964e4d8E8AC754cE'),
            balance=Balance(FVal(approve_amount)),
            location_label=user_address,
            address=string_to_evm_address('0x4EA9317D90b61fc28C418C247ad0CA8939Bbb0e9'),
            notes=f'Set auraBAL spending approval of {user_address} by 0x4EA9317D90b61fc28C418C247ad0CA8939Bbb0e9 to {approve_amount}',  # noqa: E501
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=5,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:42161/erc20:0x223738a747383d6F9f827d95964e4d8E8AC754cE'),
            balance=Balance(FVal(deposit_amount)),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} auraBAL into auraBAL vault',
            address=string_to_evm_address('0x4B5D2848678Db574Fbc2d2f629143d969a4f41Cb'),
            counterparty=CPT_AURA_FINANCE,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=6,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x4EA9317D90b61fc28C418C247ad0CA8939Bbb0e9'),
            balance=Balance(FVal(receive_amount)),
            location_label=user_address,
            notes=f'Receive {receive_amount} stkauraBAL from auraBAL vault',
            counterparty=CPT_AURA_FINANCE,
            address=ZERO_ADDRESS,
            extra_data={'deposit_events_num': 1},
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x4936f33b7B060c7336fD0e4c61316EA248DA6827']])
def test_aura_finance_claim_rewards_base(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0xffbc4716efdb4dbd7671c969599827313166fc507e2564ff1222a317d47e7a70')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str, claim_amount_1, claim_amount_2 = base_accounts[0], TimestampMS(1721018721000), '0.000001321340972471', '8.383663297617516524', '6.566591452101315364'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(gas_str)),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=18,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:8453/erc20:0x4158734D47Fc9692176B5085E0F52ee0Da5d47F1'),
            balance=Balance(FVal(claim_amount_1)),
            location_label=user_address,
            notes=f'Claim {claim_amount_1} BAL from Aura Finance',
            address=string_to_evm_address('0xEe374580BFf150be6b955954aC3b9899D890cB57'),
            counterparty=CPT_AURA_FINANCE,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=19,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:8453/erc20:0x1509706a6c66CA549ff0cB464de88231DDBe213B'),
            balance=Balance(FVal(claim_amount_2)),
            location_label=user_address,
            notes=f'Claim {claim_amount_2} AURA from Aura Finance',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0x8b2970c237656d3895588B99a8bFe977D5618201'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0x19e4057A38a730be37c4DA690b103267AAE1d75d']])
def test_aura_finance_lock_aura_from_base_to_ethereum(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0xe0a6fd1bd40451d4b42c520b41a39ab569bf4aae43b741efbe228da40fed91ad')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str, bridge_fee_amount, locked_amount = base_accounts[0], TimestampMS(1732631175000), '0.000007432156846576', '0.011914017676630994', '90'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(gas_str)),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(bridge_fee_amount)),
            location_label=user_address,
            notes=f'Pay {bridge_fee_amount} ETH as bridge fee (to Ethereum)',
            address=string_to_evm_address('0x1509706a6c66CA549ff0cB464de88231DDBe213B'),
            counterparty=CPT_AURA_FINANCE,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=132,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:8453/erc20:0x1509706a6c66CA549ff0cB464de88231DDBe213B'),
            balance=Balance(FVal(locked_amount)),
            location_label=user_address,
            notes=f'Lock {locked_amount} AURA in Aura Finance (bridged)',
            counterparty=CPT_AURA_FINANCE,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xDbE0c28c273bbB10a632B1aaf65AC2B877bb2b92']])
def test_aura_finance_lock_aura_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x69a2c2e3e7c80f7ca3207041f09bb2799b760b937ba985af65fd69faa7487336')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str, approval_amount, locked_amount = ethereum_accounts[0], TimestampMS(1732623719000), '0.002081603016233576', '115792089237316195423570985008687907853269984665640563943628.250490697661436953', '4675.24673564105539589'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(gas_str)),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=200,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:1/erc20:0xC0c293ce456fF0ED870ADd98a0828Dd4d2903DBF'),
            balance=Balance(FVal(locked_amount)),
            location_label=user_address,
            notes=f'Lock {locked_amount} AURA in auraLocker (vlAURA)',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0x3Fa73f1E5d8A792C80F426fc8F84FBF7Ce9bBCAC'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=201,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xC0c293ce456fF0ED870ADd98a0828Dd4d2903DBF'),
            balance=Balance(FVal(approval_amount)),
            location_label=user_address,
            notes=f'Set AURA spending approval of {user_address} by 0x3Fa73f1E5d8A792C80F426fc8F84FBF7Ce9bBCAC to {approval_amount}',  # noqa: E501
            address=string_to_evm_address('0x3Fa73f1E5d8A792C80F426fc8F84FBF7Ce9bBCAC'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xB3af0E54426e48D230c97aE837F34345167BE1C6']])
def test_aura_finance_booster_deposit_ethereum(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x4ed0d517c29bfd7d202efb50e7f98fdf1acc78c7f6977b55b56c354efd8275d2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_str, approval_amount, deposit_amount, receive_amount = ethereum_accounts[0], TimestampMS(1732603247000), '0.004522784347764904', '3046599999999999952014.290938920480356746', '17520.54161498940427181', '17520.54161498940427181'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            balance=Balance(FVal(gas_str)),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=159,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xfbfaD5fa9E99081da6461F36f229B5cC88A64c63'),
            balance=Balance(FVal(approval_amount)),
            location_label=user_address,
            notes=f'Set ECLP-GYD-USDT spending approval of {user_address} by 0xA57b8d98dAE62B26Ec3bcC4a365338157060B234 to {approval_amount}',  # noqa: E501
            address=string_to_evm_address('0xA57b8d98dAE62B26Ec3bcC4a365338157060B234'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=160,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:1/erc20:0xfbfaD5fa9E99081da6461F36f229B5cC88A64c63'),
            balance=Balance(FVal(deposit_amount)),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} ECLP-GYD-USDT into an Aura gauge',
            counterparty=CPT_AURA_FINANCE,
            address=string_to_evm_address('0xaF52695E1bB01A16D33D7194C28C42b10e0Dbec2'),
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=161,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0x4313428170c09ca81117a95f0418aefE3446d935'),
            balance=Balance(FVal(receive_amount)),
            location_label=user_address,
            notes=f'Receive {receive_amount} auraECLP-GYD-USDT-vault from an Aura gauge',
            counterparty=CPT_AURA_FINANCE,
            address=ZERO_ADDRESS,
            extra_data={'deposit_events_num': 1},
        ),
    ]
    assert events == expected_events
