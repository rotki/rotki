from typing import TYPE_CHECKING

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.stakedao.constants import (
    STAKEDAO_CLAIMER1,
    STAKEDAO_CLAIMER2,
    STAKEDAO_CLAIMER_OLD,
)
from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.stakedao.constants import CPT_STAKEDAO
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_BSC_BNB, A_CRV, A_CVX, A_ETH
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import globaldb_set_general_cache_values
from rotkehlchen.history.events.structures.evm_event import EvmEvent
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
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.STAKEDAO_GAUGES, '42161'),
            values=['0x0B31dA9ff8b35106B86B6203cebf94603131c75c'],
        )
        globaldb_set_general_cache_values(
            write_cursor=write_cursor,
            key_parts=(CacheType.STAKEDAO_GAUGES, '56'),
            values=['0xE36c375AD28C0822ab476Bd62A8BEAd88d9a4e34'],
        )


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x6eEC7Dd840e3c1aBbaC157bB3C14e2aCBa72bC1e']])
def test_claim_one(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x3f747b34f1d0a6c59c62b5d6c3aba8f2bd278546cd53daa131327242c7c5b02e')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1684662791000)
    amount_str = '215.403304465915246838'
    period = 1684368000
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x54dEa0D442c3254419382f0b5Fc5D245eb241569']])
def test_old_claim(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc76710a3bd4428ae8f462f75b31fcf56bbf40c4cfe2746f62259437526735073')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, gas_str, amount_str, period = TimestampMS(1673676767000), '0.002265930693617121', '1.029361212967421451', 1673481600  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x3c28C42B24B7909c8292920929f083F60C4997A6']])
def test_claim_multiple(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xc866db3fcbef6359919c444de324b6f059f299ed155f5bff00abd81537c88627')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1678952351000)
    period = 1678924800
    amount1_str = '43.57001129039620188'
    amount2_str = '41.966838515681574848'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
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
            tx_hash=tx_hash,
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
        ), EvmEvent(
            tx_hash=tx_hash,
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
        ),
    ]
    assert events == expected_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x76d5eb42A854A1cEAfFD99000341d4E4e7a4a70F']])
def test_deposit(ethereum_inquirer, ethereum_accounts, stakedao_gauges):
    tx_hash = deserialize_evm_tx_hash('0x0b98f04aeeaa4068b8c8ae0568ed236537c3573b4c3e6fd6b1924741cd5c9ef5')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    gas_amount, deposit_amount, timestamp = '0.000333982538036425', '29741.066052414178579757', TimestampMS(1742908919000)  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
        sequence_index=1,
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
        tx_hash=tx_hash,
        sequence_index=2,
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
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x5bAaC7ccda079839C9524b90dF81720834FC039f']])
def test_withdraw(ethereum_inquirer, ethereum_accounts, stakedao_gauges):
    tx_hash = deserialize_evm_tx_hash('0x1f0b98aa12fb35df17801ddfbbc0c2979ec611b50311535bad92ab5ec54f65f9')  # noqa: E501
    user_address = ethereum_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    gas_amount, cvr_reward, cvx_reward, received_amount, timestamp = '0.000731782766782389', '3.396353893656228423', '0.001648465329300485', '248892.018071224099683254', TimestampMS(1742912819000)  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
        sequence_index=2,
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
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=3,
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
        tx_hash=tx_hash,
        sequence_index=4,
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
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x65387326f9b8C3B6a83C1B3dFB43061F3ff3E508']])
def test_deposit_arb(arbitrum_one_inquirer, arbitrum_one_accounts, stakedao_gauges):
    tx_hash = deserialize_evm_tx_hash('0x433171926de6f818765b125e259244f6965993a4bc0eb055a03ee007f9e8a1e8')  # noqa: E501
    user_address = arbitrum_one_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    gas_amount, deposit_amount, timestamp = '0.00000485501', '0.000420669270502585', TimestampMS(1738238320000)  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount),
        location_label=user_address,
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.DEPOSIT,
        event_subtype=HistoryEventSubType.DEPOSIT_FOR_WRAPPED,
        asset=Asset('eip155:42161/erc20:0x186cF879186986A20aADFb7eAD50e3C20cb26CeC'),
        amount=FVal(deposit_amount),
        location_label=user_address,
        notes=f'Deposit {deposit_amount} 2BTC-ng in StakeDAO',
        counterparty=CPT_STAKEDAO,
        address=string_to_evm_address('0xfc072ead21DdA7260008aa4165907Bc27cC59329'),
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.RECEIVE_WRAPPED,
        asset=Asset('eip155:42161/erc20:0x0B31dA9ff8b35106B86B6203cebf94603131c75c'),
        amount=FVal(deposit_amount),
        location_label=user_address,
        notes=f'Receive {deposit_amount} sd2BTC-ng-vault-gauge after depositing in StakeDAO',
        counterparty=CPT_STAKEDAO,
        address=ZERO_ADDRESS,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('binance_sc_accounts', [['0xa99345367044C80D8f01d0618c44B752C4C29Bdb']])
def test_withdraw_bsc(binance_sc_inquirer, binance_sc_accounts, stakedao_gauges):
    tx_hash = deserialize_evm_tx_hash('0x0e8556a645758a6747072673fa713f98a5b3dae090b940257e5ef7c86dc73d49')  # noqa: E501
    user_address = binance_sc_accounts[0]
    events, _ = get_decoded_events_of_transaction(evm_inquirer=binance_sc_inquirer, tx_hash=tx_hash)  # noqa: E501
    gas_amount, cake_reward, received_amount, timestamp = '0.000358695', '1.156230303623121164', '2000', TimestampMS(1743674447000)  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BSC_BNB,
        amount=FVal(gas_amount),
        location_label=user_address,
        notes=f'Burn {gas_amount} BNB for gas',
        counterparty=CPT_GAS,
        address=None,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.RETURN_WRAPPED,
        asset=Asset('eip155:56/erc20:0xE36c375AD28C0822ab476Bd62A8BEAd88d9a4e34'),
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Return {received_amount} PCS-ERC20-gauge to StakeDAO',
        counterparty=CPT_STAKEDAO,
        address=string_to_evm_address('0xE36c375AD28C0822ab476Bd62A8BEAd88d9a4e34'),
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.WITHDRAWAL,
        event_subtype=HistoryEventSubType.REDEEM_WRAPPED,
        asset=Asset('eip155:56/erc20:0xb9dC6396AcFFD24E0f69Dfd3231fDaeB31514D02'),
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Withdraw {received_amount} Stable-LP from StakeDAO',
        counterparty=CPT_STAKEDAO,
        address=string_to_evm_address('0x64F19930f0250E8313D0D8b47901F377B868Cf47'),
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:56/erc20:0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82'),
        amount=FVal(cake_reward),
        location_label=user_address,
        notes=f'Claim {cake_reward} Cake from StakeDAO',
        counterparty=CPT_STAKEDAO,
        address=string_to_evm_address('0xE36c375AD28C0822ab476Bd62A8BEAd88d9a4e34'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('arbitrum_one_accounts', [['0x811e8f6d80F38A2f0f8b606cB743A950638f0aD4']])
def test_claim_rewards(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x7ce0becce93ff093c51f33c2012fd3d2dfa5118cedb1c60d9cad339ceb3e4ae4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=arbitrum_one_inquirer, tx_hash=tx_hash)  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1746073890000)),
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.00000393857'),
        location_label=(user_address := arbitrum_one_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
        address=None,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:42161/erc20:0x498Bf2B1e120FeD3ad3D42EA2165E9b73f99C1e5'),
        amount=FVal(claim_amount_1 := '0.008202419557833013'),
        location_label=user_address,
        notes=f'Claim {claim_amount_1} crvUSD from StakeDAO',
        counterparty=CPT_STAKEDAO,
        address=string_to_evm_address('0x115E05063B1F0a74b2233043694930bC703E2981'),
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:42161/erc20:0x11cDb42B0EB46D95f990BeDD4695A6e3fA034978'),
        amount=FVal(claim_amount_2 := '0.245424060931860907'),
        location_label=user_address,
        notes=f'Claim {claim_amount_2} CRV from StakeDAO',
        counterparty=CPT_STAKEDAO,
        address=string_to_evm_address('0xFC24Afa035010B4878F8ffBC94BC1ae21279cfA3'),
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:42161/erc20:0x11cDb42B0EB46D95f990BeDD4695A6e3fA034978'),
        amount=FVal(claim_amount_3 := '0.477704588685622413'),
        location_label=user_address,
        notes=f'Claim {claim_amount_3} CRV from StakeDAO',
        counterparty=CPT_STAKEDAO,
        address=string_to_evm_address('0x533C72541B918280E3492e4106e7262b8b5B1811'),
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xb6aE392c3D209BEE9dEd8A2a434A47c05F651092']])
def test_claim_bribe_with_protocolfee(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xd76c858d4e9a11d6b2cb70ca752c898728e79f40705c93d7e31b814f8f20a497')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address, gas_amount, claim_amount, timestamp, period = ethereum_accounts[0], '0.002079703956975652', '0.703793566500610594', TimestampMS(1679130407000), 1678924800  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
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
        tx_hash=tx_hash,
        sequence_index=221,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.RECEIVE,
        event_subtype=HistoryEventSubType.REWARD,
        asset=Asset('eip155:1/erc20:0x6810e776880C02933D47DB1b9fc05908e5386b96'),  # GNO
        amount=FVal(claim_amount),
        location_label=user_address,
        notes=f'Claim {claim_amount} GNO from StakeDAO veCRV bribes for the period starting at {timestamp_to_date(period, formatstr="%d/%m/%Y %H:%M:%S")}',  # noqa: E501
        counterparty=CPT_STAKEDAO,
        address=string_to_evm_address('0x7D0F747eb583D43D41897994c983F13eF7459e1f'),
    )]
    assert events == expected_events
