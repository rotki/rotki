import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.oneinch.liquidity.constants import CPT_ONEINCH_LIQUIDITY
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH, A_USDT
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

A_1INCH = Asset('eip155:1/erc20:0x111111111117dC0aa78b770fA6A738034120C302')
ETH_1INCH_POOL = string_to_evm_address('0x812b40c2cA7fAbBAc756475593fC8B1c313434FA')
A_1LP_ETH_1INCH = Asset(f'eip155:1/erc20:{ETH_1INCH_POOL}')
ETH_USDT_POOL = string_to_evm_address('0xbBa17b81aB4193455Be10741512d0E71520F43cB')
A_1LP_ETH_USDT = Asset(f'eip155:1/erc20:{ETH_USDT_POOL}')


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xbC75767E2c23fC834379C4599067dbE3174FE5F4']])
def test_oneinch_liquidity_deposit(ethereum_inquirer, ethereum_accounts):
    """Test the deposit from https://github.com/rotki/rotki/issues/1981"""
    tx_hash = deserialize_evm_tx_hash('0x0fc846fdc0343a7aa43447f7cf074d7dcb2ae4283c2c2e53e0477a2cfb196037')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1609102338000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.009274412'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=147,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_1INCH,
        amount=FVal(approve_amount := '115792089237316195423570985008687907853269984665640564038051.821129519885804696'),  # noqa: E501
        location_label=user_address,
        notes=f'Set 1INCH spending approval of {user_address} by {ETH_1INCH_POOL} to {approve_amount}',  # noqa: E501
        address=ETH_1INCH_POOL,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=148,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_ETH,
        amount=FVal(eth_amount := '2.517948895660343739'),
        location_label=user_address,
        notes=f'Deposit {eth_amount} ETH to 1inch Liquidity Protocol pool {ETH_1INCH_POOL}',
        counterparty=CPT_ONEINCH_LIQUIDITY,
        address=ETH_1INCH_POOL,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=149,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_1INCH,
        amount=FVal(oneinch_amount := '1405.762878393243835239'),
        location_label=user_address,
        notes=f'Deposit {oneinch_amount} 1INCH to 1inch Liquidity Protocol pool {ETH_1INCH_POOL}',
        counterparty=CPT_ONEINCH_LIQUIDITY,
        address=ETH_1INCH_POOL,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=150,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=A_1LP_ETH_1INCH,
        amount=FVal(lp_amount := '688'),
        location_label=user_address,
        notes=f'Receive {lp_amount} 1LP-ETH-1INCH from 1inch Liquidity Protocol pool',
        counterparty=CPT_ONEINCH_LIQUIDITY,
        address=ETH_1INCH_POOL,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xa6CE66f79EBEa1420D71B4B688c652F077Bc1331']])
def test_oneinch_liquidity_withdrawal(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x97ebe63649b077a6c5f490274431f428e67ded267bec686e49012e4adba053b2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1780991039000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.000120824534327907'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=A_1LP_ETH_1INCH,
        amount=FVal(lp_amount := '2.628872543480759388'),
        location_label=user_address,
        notes=f'Return {lp_amount} 1LP-ETH-1INCH to 1inch Liquidity Protocol pool',
        counterparty=CPT_ONEINCH_LIQUIDITY,
        address=ETH_1INCH_POOL,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_ETH,
        amount=FVal(eth_amount := '0.001729244160134287'),
        location_label=user_address,
        notes=f'Withdraw {eth_amount} ETH from 1inch Liquidity Protocol pool {ETH_1INCH_POOL}',
        counterparty=CPT_ONEINCH_LIQUIDITY,
        address=ETH_1INCH_POOL,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_1INCH,
        amount=FVal(oneinch_amount := '40.799694177311019181'),
        location_label=user_address,
        notes=f'Withdraw {oneinch_amount} 1INCH from 1inch Liquidity Protocol pool {ETH_1INCH_POOL}',  # noqa: E501
        counterparty=CPT_ONEINCH_LIQUIDITY,
        address=ETH_1INCH_POOL,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x4b0429F3db75dbA6B82c32a200C9C298ffC05839']])
def test_mooniswap_deposit(ethereum_inquirer, ethereum_accounts):
    """Test a deposit to a pool of the older Mooniswap factory"""
    tx_hash = deserialize_evm_tx_hash('0x1f736d92563259ae1feeec90f8109e31a30801e8303483750ee15817bba5e735')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1679479991000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.002885261256994148'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_ETH,
        amount=FVal(eth_amount := '0.00728986527436188'),
        location_label=user_address,
        notes=f'Deposit {eth_amount} ETH to 1inch Liquidity Protocol pool {ETH_USDT_POOL}',
        counterparty=CPT_ONEINCH_LIQUIDITY,
        address=ETH_USDT_POOL,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=A_USDT,
        amount=FVal(usdt_amount := '12.899385'),
        location_label=user_address,
        notes=f'Deposit {usdt_amount} USDT to 1inch Liquidity Protocol pool {ETH_USDT_POOL}',
        counterparty=CPT_ONEINCH_LIQUIDITY,
        address=ETH_USDT_POOL,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=A_1LP_ETH_USDT,
        amount=FVal(lp_amount := '0.007351124014184462'),
        location_label=user_address,
        notes=f'Receive {lp_amount} 1LP-ETH-USDT from 1inch Liquidity Protocol pool',
        counterparty=CPT_ONEINCH_LIQUIDITY,
        address=ETH_USDT_POOL,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x188B2d6ac1A8752Ea4Ef4ADB582646F074096aeE']])
def test_mooniswap_withdrawal(ethereum_inquirer, ethereum_accounts):
    """Test a withdrawal from a pool of the older Mooniswap factory"""
    tx_hash = deserialize_evm_tx_hash('0x6cc9a9795819e6f2ec58a0c8a640a5bf09626e504d8900c990712a3a28b5d790')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1782410459000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00015820347100082'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=A_1LP_ETH_USDT,
        amount=FVal(lp_amount := '0.002094679797874485'),
        location_label=user_address,
        notes=f'Return {lp_amount} 1LP-ETH-USDT to 1inch Liquidity Protocol pool',
        counterparty=CPT_ONEINCH_LIQUIDITY,
        address=ETH_USDT_POOL,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_ETH,
        amount=FVal(eth_amount := '0.002356990500221975'),
        location_label=user_address,
        notes=f'Withdraw {eth_amount} ETH from 1inch Liquidity Protocol pool {ETH_USDT_POOL}',
        counterparty=CPT_ONEINCH_LIQUIDITY,
        address=ETH_USDT_POOL,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=A_USDT,
        amount=FVal(usdt_amount := '3.69377'),
        location_label=user_address,
        notes=f'Withdraw {usdt_amount} USDT from 1inch Liquidity Protocol pool {ETH_USDT_POOL}',
        counterparty=CPT_ONEINCH_LIQUIDITY,
        address=ETH_USDT_POOL,
    )]
