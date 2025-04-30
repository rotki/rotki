from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.gearbox.constants import GEAR_STAKING_CONTRACT
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.gearbox.constants import CPT_GEARBOX
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_USDC
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import compute_cache_key
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import (
    CacheType,
    ChecksumEvmAddress,
    Location,
    TimestampMS,
    deserialize_evm_tx_hash,
)
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.chain.arbitrum_one.node_inquirer import ArbitrumOneInquirer
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer
    from rotkehlchen.chain.optimism.node_inquirer import OptimismInquirer


@pytest.fixture(name='setup_gearbox_cache')
def _setup_gearbox_cache(globaldb):
    """Setup the global DB cache with Gearbox pool data for testing."""
    str_chain_id = '1'
    pool_address = string_to_evm_address('0x9ef444a6d7F4A5adcd68FD5329aA5240C90E14d2')
    farming_token_address = string_to_evm_address('0x73302b63Ad4a16C498f26dB89cb27F37a72E4E04')
    lp_token_address = string_to_evm_address('0x7F5c764cBc14f9669B88837ca1490cCa17c31607')

    with globaldb.conn.write_ctx() as cursor:
        cursor.execute(  # Add pool address to cache
            'INSERT OR REPLACE INTO general_cache(key, value, last_queried_ts) VALUES(?, ?, ?)',
            (compute_cache_key((CacheType.GEARBOX_POOL_ADDRESS, str_chain_id)), pool_address, (now := ts_now())),  # noqa: E501
        )
        cursor.execute(  # Add pool name to cache
            'INSERT OR REPLACE INTO unique_cache(key, value, last_queried_ts) VALUES(?, ?, ?)',
            (compute_cache_key((CacheType.GEARBOX_POOL_NAME, pool_address, str_chain_id)), 'Farming of Trade USDC v3', now),  # noqa: E501
        )
        cursor.execute(  # Add farming token to cache
            'INSERT OR REPLACE INTO unique_cache(key, value, last_queried_ts) VALUES(?, ?, ?)',
            (compute_cache_key((CacheType.GEARBOX_POOL_FARMING_TOKEN, pool_address, str_chain_id)), farming_token_address, now),  # noqa: E501
        )
        cursor.execute(  # Add LP token to cache
            'INSERT OR REPLACE INTO general_cache(key, value, last_queried_ts) VALUES(?, ?, ?)',
            (compute_cache_key((CacheType.GEARBOX_POOL_LP_TOKENS, pool_address, str_chain_id, lp_token_address)), lp_token_address, now),  # noqa: E501
        )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_GEARBOX]])
@pytest.mark.parametrize('ethereum_accounts', [['0x3630220f243288E3EAC4C5676fC191CFf5756431']])
def test_gearbox_deposit(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        load_global_caches: list[str],
):
    tx_hash = deserialize_evm_tx_hash('0x04e3bcebf71873a5de1c4d9b40f1c97631a3958ef0d8d743a1a1b4d50361855d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp, gas, deposit_amount, lp_token_amount = TimestampMS(1716770963000), '0.0006562535', '156164.834098036387706577', '151038.694912640397702932'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=513,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_DAI,
            amount=FVal(deposit_amount),
            location_label=ethereum_accounts[0],
            notes=f'Deposit {deposit_amount} DAI to Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x1aD0780a152fE66FAf7c44A7F875A36b1bf790F0'),
        ), EvmEvent(
            sequence_index=520,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0xC853E4DA38d9Bd1d01675355b8c8f3BBC1451973'),
            amount=FVal(lp_token_amount),
            location_label=ethereum_accounts[0],
            notes=f'Receive {lp_token_amount} farmdDAIV3 after depositing in Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x1aD0780a152fE66FAf7c44A7F875A36b1bf790F0'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_GEARBOX]])
@pytest.mark.parametrize('ethereum_accounts', [['0xb99a2c4C1C4F1fc27150681B740396F6CE1cBcF5']])
def test_gearbox_deposit_usdc(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        load_global_caches: list[str],
):
    tx_hash = deserialize_evm_tx_hash('0x92d178bbe5152cad47029b0c130450848ee46084e72addd09ba955631af1325b')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp, gas, deposit_amount, lp_token_amount = TimestampMS(1716899027000), '0.004946659515956316', '6500000', '6147276.510091'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=154,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_USDC,
            amount=FVal(6500000),
            location_label=ethereum_accounts[0],
            notes=f'Set USDC spending approval of {ethereum_accounts[0]} by 0x53D5BD0E7fAa9ee3eafEf7C5572D54DB1b7f5b25 to {deposit_amount}',  # noqa: E501
            tx_hash=tx_hash,
            address=string_to_evm_address('0x53D5BD0E7fAa9ee3eafEf7C5572D54DB1b7f5b25'),
        ), EvmEvent(
            sequence_index=155,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_USDC,
            amount=FVal(deposit_amount),
            location_label=ethereum_accounts[0],
            notes=f'Deposit {deposit_amount} USDC to Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x53D5BD0E7fAa9ee3eafEf7C5572D54DB1b7f5b25'),
        ), EvmEvent(
            sequence_index=162,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0x9ef444a6d7F4A5adcd68FD5329aA5240C90E14d2'),
            amount=FVal(lp_token_amount),
            location_label=ethereum_accounts[0],
            notes=f'Receive {lp_token_amount} farmdUSDCV3 after depositing in Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x53D5BD0E7fAa9ee3eafEf7C5572D54DB1b7f5b25'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_GEARBOX]])
@pytest.mark.parametrize('ethereum_accounts', [['0x9167B9d55BA7E7D6163bAAa97C099dfE3d1D9420']])
def test_gearbox_withdraw(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        load_global_caches: list[str],
):
    tx_hash = deserialize_evm_tx_hash('0xb286e618ec2e5961c696df1855006dea0343fb635c7f199621f8592db342dfba')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp, gas, lp_amount, withdrawn = TimestampMS(1716739091000), '0.002506078391975991', '29394.203983328624199078', '30388.281725016794033508'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=500,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0xC853E4DA38d9Bd1d01675355b8c8f3BBC1451973'),
            amount=FVal(lp_amount),
            location_label=ethereum_accounts[0],
            notes=f'Return {lp_amount} farmdDAIV3',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x1aD0780a152fE66FAf7c44A7F875A36b1bf790F0'),
        ), EvmEvent(
            sequence_index=504,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_DAI,
            amount=FVal(withdrawn),
            location_label=ethereum_accounts[0],
            notes=f'Withdraw {withdrawn} DAI from Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0xe7146F53dBcae9D6Fa3555FE502648deb0B2F823'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_GEARBOX]])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x0e414c1c4780df6c09c2f1070990768D44B70b1D']])
def test_gearbox_deposit_arbitrum(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
        load_global_caches: list[str],
):
    tx_hash = deserialize_evm_tx_hash('0x00db27b8c09c9ec4478f27da7e40b90afbb577cfb4822536eab5a52dcae321e6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp, gas, deposit_amount, lp_token_amount = TimestampMS(1716815867000), '0.00000249681', '0.001', '0.00098428586189406'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(deposit_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Deposit {deposit_amount} ETH to Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x78c1B41b825f89FAE4736878Fa63752F8D789BD6'),
        ), EvmEvent(
            sequence_index=40,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x6773fF780Dd38175247795545Ee37adD6ab6139a'),
            amount=FVal(lp_token_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Receive {lp_token_amount} farmdWETHV3 after depositing in Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x78c1B41b825f89FAE4736878Fa63752F8D789BD6'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_GEARBOX]])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x0e414c1c4780df6c09c2f1070990768D44B70b1D']])
def test_gearbox_deposit_arbitrum_lp(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
        load_global_caches: list[str],
):
    tx_hash = deserialize_evm_tx_hash('0x7dbb02839dab23bc87ed6f4f5899fc77986c576e6fedf16cfbd9751fbe09e2eb')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp, gas, deposit_amount, lp_token_amount = TimestampMS(1716899425000), '0.0000022431', '0.001', '0.000984005521495659'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(deposit_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Deposit {deposit_amount} ETH to Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0xA909d7924a5aeb6c31c6A3AD30E9950d4B40F8cB'),
        ), EvmEvent(
            sequence_index=33,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x04419d3509f13054f60d253E0c79491d9E683399'),
            amount=FVal(lp_token_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Receive {lp_token_amount} dWETHV3 after providing liquidity in Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_GEARBOX]])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x3a212d3d7504dC4A39E21C731d0E80b114A2108b']])
def test_gearbox_withdraw_arbitrum(
        arbitrum_one_inquirer: 'EthereumInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
        load_global_caches: list[str],
):
    tx_hash = deserialize_evm_tx_hash('0x9b3f388e53c6b0f2eb12c323aebb05d47e27f6d9f511bd1176ed826a351c6c06')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp, gas, lp_amount, withdrawn = TimestampMS(1717435594000), '0.00000250989', '0.7', '0.712544409227268693'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=A_ETH,
            amount=FVal(withdrawn),
            location_label=arbitrum_one_accounts[0],
            notes=f'Withdraw {withdrawn} ETH from Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x78c1B41b825f89FAE4736878Fa63752F8D789BD6'),
        ), EvmEvent(
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x6773fF780Dd38175247795545Ee37adD6ab6139a'),
            amount=FVal(lp_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Return {lp_amount} farmdWETHV3',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x78c1B41b825f89FAE4736878Fa63752F8D789BD6'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_GEARBOX]])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x7b007E8c0f77B50bEC8009f0e97F523DBa6FE506']])
def test_gearbox_deposit_usdc_arbitrum(
        arbitrum_one_inquirer: 'ArbitrumOneInquirer',
        arbitrum_one_accounts: list['ChecksumEvmAddress'],
        load_global_caches: list[str],
):
    tx_hash = deserialize_evm_tx_hash('0xc7a3b95862eba49a86b8eefe81837ea141037feda8c0da236d9c3adb370fdfb3')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp, gas, deposit_amount, lp_token_amount, approval_amount = TimestampMS(1717508317000), '0.00000368093', '125.164428', '121.463529', '125.164428'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=arbitrum_one_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=7,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8'),
            amount=FVal(approval_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Set USDC.e spending approval of {arbitrum_one_accounts[0]} by 0xD72e1B9A5FC74b35435f71603a81dAE217c2D863 to {approval_amount}',  # noqa: E501
            tx_hash=tx_hash,
            address=string_to_evm_address('0xD72e1B9A5FC74b35435f71603a81dAE217c2D863'),
        ), EvmEvent(
            sequence_index=8,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8'),
            amount=FVal(deposit_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Deposit {deposit_amount} USDC.e to Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0xD72e1B9A5FC74b35435f71603a81dAE217c2D863'),
        ), EvmEvent(
            sequence_index=9,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8'),
            amount=ZERO,
            location_label=arbitrum_one_accounts[0],
            notes=f'Revoke USDC.e spending approval of {arbitrum_one_accounts[0]} by 0xD72e1B9A5FC74b35435f71603a81dAE217c2D863',  # noqa: E501
            tx_hash=tx_hash,
            address=string_to_evm_address('0xD72e1B9A5FC74b35435f71603a81dAE217c2D863'),
        ), EvmEvent(
            sequence_index=17,
            timestamp=timestamp,
            location=Location.ARBITRUM_ONE,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:42161/erc20:0x608F9e2E8933Ce6b39A8CddBc34a1e3E8D21cE75'),
            amount=FVal(lp_token_amount),
            location_label=arbitrum_one_accounts[0],
            notes=f'Receive {lp_token_amount} farmdUSDCV3 after depositing in Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0xD72e1B9A5FC74b35435f71603a81dAE217c2D863'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_GEARBOX]])
@pytest.mark.parametrize('optimism_accounts', [['0xb8150a1B6945e75D05769D685b127b41E6335Bbc']])
def test_gearbox_deposit_optimism(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
        load_global_caches: list[str],
):
    tx_hash = deserialize_evm_tx_hash('0x1dc1803865e909909bf20a82b0d88b476bcac13c7a0efa57c531baa06b0cb27e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp, gas, deposit_amount, lp_token_amount = TimestampMS(1714433685000), '0.000010672234173866', '0.1', '0.099957406908026936'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=optimism_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=A_ETH,
            amount=FVal(deposit_amount),
            location_label=optimism_accounts[0],
            notes=f'Deposit {deposit_amount} ETH to Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0xEa8ca794aEe0f998Ed6AB50F4042c28807E546Eb'),
        ), EvmEvent(
            sequence_index=97,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:10/erc20:0x704c4C9F0d29257E5b0E526b20b48EfFC8f758b2'),
            amount=FVal(lp_token_amount),
            location_label=optimism_accounts[0],
            notes=f'Receive {lp_token_amount} farmdWETHV3 after depositing in Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0xEa8ca794aEe0f998Ed6AB50F4042c28807E546Eb'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_GEARBOX]])
@pytest.mark.parametrize('optimism_accounts', [['0xb8150a1B6945e75D05769D685b127b41E6335Bbc']])
def test_gearbox_deposit_usdc_optimism(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
        load_global_caches: list[str],
):
    tx_hash = deserialize_evm_tx_hash('0x25baef6edb2fae8fde18b7ee49dbba94bdaa500db1388cc5b22bdb4ba953d7b4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp, gas, deposit_amount, approval_amount = TimestampMS(1714434001000), '0.000011648221611152', '300', '394.3605'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=optimism_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=3,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            amount=FVal(deposit_amount),
            location_label=optimism_accounts[0],
            notes=f'Deposit {deposit_amount} USDC.e to Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x931BC69a32BE7A36f9B00Bf63D17Fa8fB9a8C525'),
        ), EvmEvent(
            sequence_index=4,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            amount=FVal(approval_amount),
            location_label=optimism_accounts[0],
            notes=f'Set USDC.e spending approval of {optimism_accounts[0]} by 0x931BC69a32BE7A36f9B00Bf63D17Fa8fB9a8C525 to {approval_amount}',  # noqa: E501
            tx_hash=tx_hash,
            address=string_to_evm_address('0x931BC69a32BE7A36f9B00Bf63D17Fa8fB9a8C525'),
        ), EvmEvent(
            sequence_index=12,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:10/erc20:0x73302b63Ad4a16C498f26dB89cb27F37a72E4E04'),
            amount=FVal(deposit_amount),
            location_label=optimism_accounts[0],
            notes=f'Receive {deposit_amount} farmdUSDCV3 after depositing in Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x931BC69a32BE7A36f9B00Bf63D17Fa8fB9a8C525'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_GEARBOX]])
@pytest.mark.parametrize('optimism_accounts', [['0x42ccF4f456D7c7fEBF274242CACcD74AAa0a53d7']])
def test_gearbox_withdraw_optimism_usdc(
        optimism_inquirer: 'OptimismInquirer',
        optimism_accounts: list['ChecksumEvmAddress'],
        load_global_caches: list[str],
):
    tx_hash = deserialize_evm_tx_hash('0x03569fa219dd445c120a38eb294a21feee8da7f0e1d3b6aed1d87a3ca519b16d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp, gas, lp_amount = TimestampMS(1712552439000), '0.000001104938540339', '50'
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=optimism_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=125,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:10/erc20:0x73302b63Ad4a16C498f26dB89cb27F37a72E4E04'),
            amount=FVal(lp_amount),
            location_label=optimism_accounts[0],
            notes=f'Return {lp_amount} farmdUSDCV3',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x931BC69a32BE7A36f9B00Bf63D17Fa8fB9a8C525'),
        ), EvmEvent(
            sequence_index=129,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
            amount=FVal(lp_amount),
            location_label=optimism_accounts[0],
            notes=f'Withdraw {lp_amount} USDC.e from Gearbox',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            address=string_to_evm_address('0x5520dAa93A187f4Ec67344e6D2C4FC9B080B6A35'),
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x0e414c1c4780df6c09c2f1070990768D44B70b1D']])
def test_gearbox_staking(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0x5de7647a4c8f8ca1e5434725dd09b27ce05e41954d72c3f1f4d639c8b7019f4a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas, stake_amount = TimestampMS(1718177819000), '0.0008970313372218', '260.869836197270890866'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=509,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xBa3335588D9403515223F109EdC4eB7269a9Ab5D'),
            amount=FVal(stake_amount),
            location_label=ethereum_accounts[0],
            notes=f'Set GEAR spending approval of {ethereum_accounts[0]} by {GEAR_STAKING_CONTRACT} to {stake_amount}',  # noqa: E501
            tx_hash=tx_hash,
            address=GEAR_STAKING_CONTRACT,
        ), EvmEvent(
            sequence_index=510,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xBa3335588D9403515223F109EdC4eB7269a9Ab5D'),
            amount=ZERO,
            location_label=ethereum_accounts[0],
            notes=f'Revoke GEAR spending approval of {ethereum_accounts[0]} by {GEAR_STAKING_CONTRACT}',  # noqa: E501
            tx_hash=tx_hash,
            address=GEAR_STAKING_CONTRACT,
        ), EvmEvent(
            sequence_index=511,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.DEPOSIT_ASSET,
            asset=Asset('eip155:1/erc20:0xBa3335588D9403515223F109EdC4eB7269a9Ab5D'),
            amount=FVal(stake_amount),
            location_label='0x0e414c1c4780df6c09c2f1070990768D44B70b1D',
            notes=f'Stake {stake_amount} GEAR',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            product=EvmProduct.STAKING,
            address=GEAR_STAKING_CONTRACT,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xe4283e107fB8E96F3175955EC7269afb51ECa6ea']])
def test_gearbox_unstaking(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
):
    tx_hash = deserialize_evm_tx_hash('0xb50badadb71b7c8c4ab2d0f9691931396322b2395da2396bee1ed65755e3882a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas, stake_amount = TimestampMS(1717241039000), '0.000287410296179888', '1210105.252774990252868034'  # noqa: E501
    expected_events = [
        EvmEvent(
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=ethereum_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            tx_hash=tx_hash,
            counterparty=CPT_GAS,
        ), EvmEvent(
            sequence_index=308,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.STAKING,
            event_subtype=HistoryEventSubType.REMOVE_ASSET,
            asset=Asset('eip155:1/erc20:0xBa3335588D9403515223F109EdC4eB7269a9Ab5D'),
            amount=FVal(stake_amount),
            location_label=ethereum_accounts[0],
            notes=f'Unstake {stake_amount} GEAR',
            tx_hash=tx_hash,
            counterparty=CPT_GEARBOX,
            product=EvmProduct.STAKING,
            address=GEAR_STAKING_CONTRACT,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_GEARBOX]])
@pytest.mark.parametrize('ethereum_accounts', [['0xC5d494aa0CBabD7871af0Ef122fB410Fa25c3379']])
def test_gearbox_claim_from_angle(
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        load_global_caches: list[str],
):
    tx_hash = deserialize_evm_tx_hash('0x6539828c45548f323febc685498457880b0651375ca5077338a162676574048c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp, gas, gear_amount = TimestampMS(1745790011000), '0.00005385590405946', '1412.737469800492924993'  # noqa: E501
    assert events == [EvmEvent(
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas),
        location_label=(user_account := ethereum_accounts[0]),
        notes=f'Burn {gas} ETH for gas',
        tx_hash=tx_hash,
        counterparty=CPT_GAS,
    ), EvmEvent(
        sequence_index=371,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:1/erc20:0xBa3335588D9403515223F109EdC4eB7269a9Ab5D'),
        amount=FVal(gear_amount),
        location_label=user_account,
        notes=f'Claim {gear_amount} GEAR reward from Gearbox',
        tx_hash=tx_hash,
        counterparty=CPT_GEARBOX,
        address=string_to_evm_address('0x3Ef3D8bA38EBe18DB133cEc108f4D14CE00Dd9Ae'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('load_global_caches', [[CPT_GEARBOX]])
@pytest.mark.parametrize('ethereum_accounts', [['0xC5d494aa0CBabD7871af0Ef122fB410Fa25c3379']])
def test_gearbox_claim(
        setup_gearbox_cache,
        ethereum_inquirer: 'EthereumInquirer',
        ethereum_accounts: list['ChecksumEvmAddress'],
        load_global_caches: list[str],
):
    tx_hash = deserialize_evm_tx_hash('0x0e0efdf539b2882192958891ff9d0005297e0301ecd594763c87da8a84f1aca8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
        load_global_caches=load_global_caches,
    )
    timestamp, gas, gear_amount = TimestampMS(1745790059000), '0.000026898409237966', '46983.327727303683938594'  # noqa: E501
    assert events == [EvmEvent(
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas),
        location_label=(user_account := ethereum_accounts[0]),
        notes=f'Burn {gas} ETH for gas',
        tx_hash=tx_hash,
        counterparty=CPT_GAS,
    ), EvmEvent(
        sequence_index=339,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:1/erc20:0xBa3335588D9403515223F109EdC4eB7269a9Ab5D'),
        amount=FVal(gear_amount),
        location_label=user_account,
        notes=f'Claim {gear_amount} GEAR reward from Gearbox',
        tx_hash=tx_hash,
        counterparty=CPT_GEARBOX,
        address=string_to_evm_address('0x9ef444a6d7F4A5adcd68FD5329aA5240C90E14d2'),
    )]
