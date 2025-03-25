from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.stakedao.constants import (
    STAKEDAO_CLAIMER1,
    STAKEDAO_CLAIMER2,
    STAKEDAO_CLAIMER_OLD,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.stakedao.constants import CPT_STAKEDAO
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_CRV, A_CVX, A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.history.events.structures.evm_event import EvmEvent, EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import CacheType, Location, TimestampMS, deserialize_evm_tx_hash
from rotkehlchen.utils.misc import timestamp_to_date

if TYPE_CHECKING:
    from rotkehlchen.globaldb.handler import GlobalDBHandler


@pytest.fixture(name='stakedao_gauges')
def _stakedao_gauges(globaldb: 'GlobalDBHandler') -> None:
    with globaldb.conn.write_ctx() as write_cursor:
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.STAKEDAO_GAUGES, '1'),
            values=[
                '0x41639ABcA04c22e80326A96C8fE2882C97BaEb6e',
                '0xf0A20878e03FF47Dc32E5c67D97c41cD3fd173B3',
            ],
        )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x6eEC7Dd840e3c1aBbaC157bB3C14e2aCBa72bC1e']])
def test_claim_one(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0x3f747b34f1d0a6c59c62b5d6c3aba8f2bd278546cd53daa131327242c7c5b02e')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    timestamp = TimestampMS(1684662791000)
    amount_str = '215.403304465915246838'
    period = 1684368000
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.003543266133945936'),
            location_label=user_address,
            notes='Burn 0.003543266133945936 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=580,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_CRV,
            amount=FVal(amount_str),
            location_label=user_address,
            notes=f'Claim {amount_str} CRV from StakeDAO veCRV bribes for the period starting at {timestamp_to_date(period, formatstr="%d/%m/%Y %H:%M:%S")}',  # noqa: E501
            counterparty=CPT_STAKEDAO,
            address=STAKEDAO_CLAIMER2,
            product=EvmProduct.BRIBE,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x54dEa0D442c3254419382f0b5Fc5D245eb241569']])
def test_old_claim(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xc76710a3bd4428ae8f462f75b31fcf56bbf40c4cfe2746f62259437526735073')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    timestamp, gas_str, amount_str, period = TimestampMS(1673676767000), '0.002265930693617121', '1.029361212967421451', 1673481600  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_str),
            location_label=user_address,
            notes=f'Burn {gas_str} ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=377,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=Asset('eip155:1/erc20:0x41D5D79431A913C4aE7d69a668ecdfE5fF9DFB68'),
            amount=FVal(amount_str),
            location_label=user_address,
            notes=f'Claim {amount_str} INV from StakeDAO veCRV bribes for the period starting at {timestamp_to_date(period, formatstr="%d/%m/%Y %H:%M:%S")}',  # noqa: E501
            counterparty=CPT_STAKEDAO,
            address=STAKEDAO_CLAIMER_OLD,
            product=EvmProduct.BRIBE,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3c28C42B24B7909c8292920929f083F60C4997A6']])
def test_claim_multiple(ethereum_inquirer, ethereum_accounts):
    tx_hex = deserialize_evm_tx_hash('0xc866db3fcbef6359919c444de324b6f059f299ed155f5bff00abd81537c88627')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    timestamp = TimestampMS(1678952351000)
    period = 1678924800
    amount1_str = '43.57001129039620188'
    amount2_str = '41.966838515681574848'
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.002833214770290904'),
            location_label=user_address,
            notes='Burn 0.002833214770290904 ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=328,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_CRV,
            amount=FVal(amount1_str),
            location_label=user_address,
            notes=f'Claim {amount1_str} CRV from StakeDAO veCRV bribes for the period starting at {timestamp_to_date(period, formatstr="%d/%m/%Y %H:%M:%S")}',  # noqa: E501
            counterparty=CPT_STAKEDAO,
            address=STAKEDAO_CLAIMER1,
            product=EvmProduct.BRIBE,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=330,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_CRV,
            amount=FVal(amount2_str),
            location_label=user_address,
            notes=f'Claim {amount2_str} CRV from StakeDAO veCRV bribes for the period starting at {timestamp_to_date(period, formatstr="%d/%m/%Y %H:%M:%S")}',  # noqa: E501
            counterparty=CPT_STAKEDAO,
            address=STAKEDAO_CLAIMER1,
            product=EvmProduct.BRIBE,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x76d5eb42A854A1cEAfFD99000341d4E4e7a4a70F']])
def test_deposit(ethereum_inquirer, ethereum_accounts, stakedao_gauges):
    tx_hex = deserialize_evm_tx_hash('0x0b98f04aeeaa4068b8c8ae0568ed236537c3573b4c3e6fd6b1924741cd5c9ef5')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    gas_amount, deposit_amount, timestamp = '0.000333982538036425', '29741.066052414178579757', TimestampMS(1742908919000)  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=800,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.DEPOSIT,
            event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
            asset=Asset('eip155:1/erc20:0x08BfA22bB3e024CDfEB3eca53c0cb93bF59c4147'),
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Deposit {deposit_amount} eUSDUSDC in StakeDAO',
            counterparty=CPT_STAKEDAO,
            address=string_to_evm_address('0x3BC2512fAa5074fFdA24DCb4994e264Cb8C64BB8'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=811,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
            asset=Asset('eip155:1/erc20:0x41639ABcA04c22e80326A96C8fE2882C97BaEb6e'),
            amount=FVal(deposit_amount),
            location_label=user_address,
            notes=f'Receive {deposit_amount} sdeUSDUSDC-gauge after depositing in StakeDAO',
            counterparty=CPT_STAKEDAO,
            address=ZERO_ADDRESS,
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5bAaC7ccda079839C9524b90dF81720834FC039f']])
def test_withdraw(ethereum_inquirer, ethereum_accounts, stakedao_gauges):
    tx_hex = deserialize_evm_tx_hash('0x1f0b98aa12fb35df17801ddfbbc0c2979ec611b50311535bad92ab5ec54f65f9')  # noqa: E501
    evmhash = deserialize_evm_tx_hash(tx_hex)
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hex)
    gas_amount, cvr_reward, cvx_reward, received_amount, timestamp = '0.000731782766782389', '3.396353893656228423', '0.001648465329300485', '248892.018071224099683254', TimestampMS(1742912819000)  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=evmhash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas_amount),
            location_label=user_address,
            notes=f'Burn {gas_amount} ETH for gas',
            counterparty=CPT_GAS,
            address=None,
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.RETURN_WRAPPED,
            asset=Asset('eip155:1/erc20:0xf0A20878e03FF47Dc32E5c67D97c41cD3fd173B3'),
            amount=FVal(received_amount),
            location_label=user_address,
            notes=f'Return {received_amount} sdalUSDsDOLA-gauge to StakeDAO',
            counterparty=CPT_STAKEDAO,
            address=string_to_evm_address('0xf0A20878e03FF47Dc32E5c67D97c41cD3fd173B3'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_CRV,
            amount=FVal(cvr_reward),
            location_label=user_address,
            notes=f'Claim {cvr_reward} CRV from StakeDAO',
            counterparty=CPT_STAKEDAO,
            address=string_to_evm_address('0xf0A20878e03FF47Dc32E5c67D97c41cD3fd173B3'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.RECEIVE,
            event_subtype=HistoryEventSubType.REWARD,
            asset=A_CVX,
            amount=FVal(cvx_reward),
            location_label=user_address,
            notes=f'Claim {cvx_reward} CVX from StakeDAO',
            counterparty=CPT_STAKEDAO,
            address=string_to_evm_address('0xf0A20878e03FF47Dc32E5c67D97c41cD3fd173B3'),
        ), EvmEvent(
            tx_hash=evmhash,
            sequence_index=329,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.WITHDRAWAL,
            event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
            asset=Asset('eip155:1/erc20:0x460638e6F7605B866736e38045C0DE8294d7D87f'),
            amount=FVal(received_amount),
            location_label=user_address,
            notes=f'Withdraw {received_amount} alUSDsDOLA from StakeDAO',
            counterparty=CPT_STAKEDAO,
            address=string_to_evm_address('0x464A190dc43aD8f706d7d90d2951F700226A47Ef'),
        ),
    ]
    assert events == expected_events
