import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.base.modules.runmoney.constants import (
    CPT_RUNMONEY,
    RUNMONEY_CONTRACT_ADDRESS,
)
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants import ONE
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.unit.test_types import LEGACY_TESTS_INDEXER_ORDER
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('base_accounts', [['0x533D5EcCdd097DE447E4142788dE58f341a4D619']])
def test_join_runmoney(base_inquirer, base_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0xc1eb69ba80f10a7e45781f6da36f95c45300e7130db7988ac2e618659cb9a8a7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        timestamp=(timestamp := TimestampMS(1750361627000)),
        sequence_index=0,
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000003052725765774')),
        location_label=(user := base_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        timestamp=timestamp,
        sequence_index=1,
        location=Location.BASE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=(membership_amount := FVal('0.0125')),
        location_label=user,
        notes=f'Pay {membership_amount} ETH membership fee to join Runmoney club',
        counterparty=CPT_RUNMONEY,
        address=RUNMONEY_CONTRACT_ADDRESS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        timestamp=timestamp,
        sequence_index=2,
        location=Location.BASE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:8453/erc721:0x1089Db83561d4c9B68350E1c292279817AC6c8DA/21'),
        amount=ONE,
        location_label=user,
        address=RUNMONEY_CONTRACT_ADDRESS,
        notes='Receive Runmoney membership NFT with id 21 for joining the club',
        counterparty=CPT_RUNMONEY,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('base_accounts', [['0x533D5EcCdd097DE447E4142788dE58f341a4D619']])
def test_stake(base_inquirer, base_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x1d6b85ce1128d5f7b9d49480f6ee516dae0af1e7da7ee6baef03844c9ca76502')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        timestamp=(timestamp := TimestampMS(1750361935000)),
        sequence_index=0,
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000000503994279338')),
        location_label=(user := base_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        timestamp=timestamp,
        sequence_index=245,
        location=Location.BASE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
        amount=(deposit_amount := FVal('50')),
        location_label=user,
        notes=f'Deposit {deposit_amount} USDC into Runmoney',
        counterparty=CPT_RUNMONEY,
        address=RUNMONEY_CONTRACT_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('base_accounts', [['0xCB965C4e41Ac688cbf3387872c6DB24ba2547dbf']])
def test_unstake(base_inquirer, base_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0x18353a471cc229f45b723e50d976187dd73f8fb9b39c5529e1a5cafc51f9b4ce')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        timestamp=(timestamp := TimestampMS(1745189763000)),
        sequence_index=0,
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000000442649593384')),
        location_label=(user := base_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        timestamp=timestamp,
        sequence_index=640,
        location=Location.BASE,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
        amount=(withdrawal_amount := FVal('20')),
        location_label=user,
        notes=f'Withdraw {withdrawal_amount} USDC from Runmoney',
        counterparty=CPT_RUNMONEY,
        address=RUNMONEY_CONTRACT_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('db_settings', LEGACY_TESTS_INDEXER_ORDER)
@pytest.mark.parametrize('base_accounts', [['0xfDe4Bef9B6060cE3a214FbC220677a13535CEb9A']])
def test_claim_bonuses(base_inquirer, base_accounts) -> None:
    tx_hash = deserialize_evm_tx_hash('0xed5e059672f5b2d7483e9fabb9239adfa5c8ae93605494a7e09e638ee8f1b13f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        timestamp=(timestamp := TimestampMS(1749456433000)),
        sequence_index=0,
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=(gas_amount := FVal('0.000005462780797336')),
        location_label=(user := base_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        timestamp=timestamp,
        sequence_index=83,
        location=Location.BASE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),
        amount=(usdc_interest_amount := FVal('0.832211')),
        location_label=user,
        notes=f'Claim {usdc_interest_amount} USDC as interest earned from Runmoney',
        counterparty=CPT_RUNMONEY,
        address=string_to_evm_address('0x4e65fE4DbA92790696d040ac24Aa414708F5c0AB'),
    ), EvmEvent(
        tx_ref=tx_hash,
        timestamp=timestamp,
        sequence_index=88,
        location=Location.BASE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:8453/erc20:0x4200000000000000000000000000000000000006'),
        amount=(weth_interest_amount := FVal('0.000063143855092025')),
        location_label=user,
        notes=f'Claim {weth_interest_amount} WETH as interest earned from Runmoney',
        counterparty=CPT_RUNMONEY,
        address=string_to_evm_address('0xD4a0e0b9149BCee3C920d2E00b5dE09138fd8bb7'),
    )]
