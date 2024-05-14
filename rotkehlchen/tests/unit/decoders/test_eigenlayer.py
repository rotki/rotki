import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.eigenlayer.constants import (
    CPT_EIGENLAYER,
    EIGEN_TOKEN_ID,
    EIGENLAYER_AIRDROP_DISTRIBUTOR,
    EIGENLAYER_STRATEGY_MANAGER,
)
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xbec0937E0E99425a886B99A3b956C7aC6C39aA12']])
def test_deposit_token(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x716b15f5088ff469d7d31680535d35b085e1c3de25255c7849e5955a59df8d31')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, gas_amount = TimestampMS(1702926167000), '0.049006058268043653'
    deposited_amount = '5.740516176725108094'
    strategy_addr = string_to_evm_address('0x0Fe4F44beE93503346A3Ac9EE5A26b130a5796d6')
    a_sweth = Asset('eip155:1/erc20:0xf951E335afb289353dc249e82926178EaC7DEd78')
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=112,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=a_sweth,
        balance=Balance(amount=ZERO),
        location_label=ethereum_accounts[0],
        notes=f'Revoke swETH spending approval of {ethereum_accounts[0]} by {EIGENLAYER_STRATEGY_MANAGER}',  # noqa: E501
        address=EIGENLAYER_STRATEGY_MANAGER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=113,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=a_sweth,
        balance=Balance(amount=FVal(deposited_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Deposit {deposited_amount} swETH in EigenLayer',
        counterparty=CPT_EIGENLAYER,
        extra_data={'strategy': strategy_addr},
        product=EvmProduct.STAKING,
        address=strategy_addr,
    )]
    assert events == expected_events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x47E50634E32212F43713Bf4e4A86E6275AcD456d']])
def test_withdraw(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x00bdab08d05bd68f8f863e35a8dbe435978481dcbf15faf7276da30a5bfee971')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, gas_amount = TimestampMS(1707668387000), '0.004606768190817408'
    withdrawn_amount = '0.407049270448991651'
    strategy_addr = string_to_evm_address('0x0Fe4F44beE93503346A3Ac9EE5A26b130a5796d6')
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=152,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.REMOVE_ASSET,
        asset=Asset('eip155:1/erc20:0xf951E335afb289353dc249e82926178EaC7DEd78'),
        balance=Balance(amount=FVal(withdrawn_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Unstake {withdrawn_amount} swETH from EigenLayer',
        counterparty=CPT_EIGENLAYER,
        product=EvmProduct.STAKING,
        address=strategy_addr,
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xabe8430e3f0BeCa32915dA84E530f81A01379953']])
def test_airdrop_claim(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x0a72c7bf0fe1808035f8df466a70453f29c6b57d0bec46913d993a19ef72265c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, gas_amount, claim_amount = TimestampMS(1715680739000), '0.00074757962836592', '110'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=253,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.AIRDROP,
        asset=Asset(EIGEN_TOKEN_ID),
        balance=Balance(amount=FVal(claim_amount)),
        location_label=ethereum_accounts[0],
        notes='Claim 110 EIGEN from the Eigenlayer airdrop',
        counterparty=CPT_EIGENLAYER,
        address=EIGENLAYER_AIRDROP_DISTRIBUTOR,
    )]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x65151A6343b16c38286f31fcC93e20246629cF8c']])
def test_stake_eigen(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x4da63226965a8b0584f137efa934106cd0cb7a15b536d6f659945cfd4c260b4e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp, gas_amount, staked_amount = TimestampMS(1715684387000), '0.00141296787957222', '110'
    a_eigen, strategy_addr = Asset(EIGEN_TOKEN_ID), '0xaCB55C530Acdb2849e6d4f36992Cd8c9D50ED8F7'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=206,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=a_eigen,
        balance=Balance(amount=ZERO),
        location_label=ethereum_accounts[0],
        notes=f'Revoke EIGEN spending approval of {ethereum_accounts[0]} by {EIGENLAYER_STRATEGY_MANAGER}',  # noqa: E501
        address=EIGENLAYER_STRATEGY_MANAGER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=207,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.STAKING,
        event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
        asset=a_eigen,
        balance=Balance(amount=FVal(staked_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Deposit {staked_amount} EIGEN in EigenLayer',
        counterparty=CPT_EIGENLAYER,
        extra_data={'strategy': strategy_addr},
        product=EvmProduct.STAKING,
        address=strategy_addr,
    )]
    assert events == expected_events
