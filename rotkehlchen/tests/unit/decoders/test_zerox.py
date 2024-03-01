from typing import Final
import pytest

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.zerox.constants import ZEROX_ROUTER
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.zerox.constants import CPT_ZEROX
from rotkehlchen.constants.assets import A_ETH, A_USDC, A_USDT
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

A_AI: Final = Asset(strethaddress_to_identifier('0x2598c30330D5771AE9F983979209486aE26dE875'))
A_DRGN: Final = Asset(strethaddress_to_identifier('0x419c4dB4B9e25d6Db2AD9691ccb832C8D9fDA05E'))
A_MYRIA: Final = Asset(strethaddress_to_identifier('0xA0Ef786Bf476fE0810408CaBA05E536aC800ff86'))
A_LFG: Final = Asset(strethaddress_to_identifier('0x40a9A694197A0b4B92f2aAd48Da6bC1b6Ff194e9'))
A_BANANA: Final = Asset(strethaddress_to_identifier('0x38E68A37E401F7271568CecaAc63c6B1e19130B4'))
A_OXN: Final = Asset(strethaddress_to_identifier('0x9012744B7A564623b6C3E40b144fc196bdeDf1A9'))
A_RAINI: Final = Asset(strethaddress_to_identifier('0xeB953eDA0DC65e3246f43DC8fa13f35623bDd5eD'))
A_PRIME: Final = Asset(strethaddress_to_identifier('0xb23d80f5FefcDDaa212212F028021B41DEd428CF'))
A_TSUKA: Final = Asset(strethaddress_to_identifier('0xc5fB36dd2fb59d3B98dEfF88425a3F425Ee469eD'))
A_SHIB: Final = Asset(strethaddress_to_identifier('0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE'))
A_LMWR: Final = Asset(strethaddress_to_identifier('0x628A3b2E302C7e896AcC432D2d0dD22B6cb9bc88'))


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xaE84961b9FA7412fEAEf209fD8f50C4F8Ef4D8fD']])
def test_sell_to_uniswap(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xb9827174e182a1b8df3507d13c5cedccdc974c4edd5d66f59355f7e9758b9006')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1709225123000)
    swap_amount, received_amount, gas_fees = '12.425145745058641', '646.553802069266414457', '0.018008266883477871'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BANANA,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} BANANA via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_OXN,
        balance=Balance(amount=FVal(received_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} OxN as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xc2aAd9386835C90deC9d669e35c128461E6102CA']])
def test_sell_eth_for_token_to_uniswap_v3(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x5b7719016f7d7d3d8ed9d4d86afd0e0079551d0a7795f70f01764ce5eaa44478')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1709222447000)
    swap_amount, received_amount, gas_fees = '0.2882978462709', '85192.182824334037015387', '0.007717607607009392'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} ETH via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_MYRIA,
        balance=Balance(amount=FVal(received_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} MYRIA as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xed288d0261421C7cf36a56f23297cD5F4635A089']])
def test_sell_token_for_eth_to_uniswap_v3(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x68416e19252c678cdf67ae9b7adff742d78f95cea3c3f0582d3dc930340e5bdf')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1709225147000)
    swap_amount, received_amount, gas_fees = '150000', '1.446309922122136822', '0.013066559749685724'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_LFG,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} @LFG via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        balance=Balance(amount=FVal(received_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} ETH as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xCCD54C835d7199ceEE2AedA4722C69eeeA6E606D']])
def test_sell_token_for_token_to_uniswap_v3(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6efe8a18de9ca3183bdb319be445f1b0b9041c0e8208fa04a58ee276b54574dd')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1709054219000)
    swap_amount, received_amount, gas_fees = '26035459.499107021225491254', '6627.784156933620641174', '0.011785737692958302'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_AI,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} AI via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_DRGN,
        balance=Balance(amount=FVal(received_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} DRGN as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xddb143606305559e6b69843c1f53f2689D2aB605']])
def test_multiplex_batch_sell_eth_for_token(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xa151bc4f1c69591598386eaa65761cefd706cbfe0a1a340d8856dbfe2c3bd8c5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1709282363000)
    swap_amount, received_amount, gas_fees = '1.160624381328078', '155577.466855002838240404', '0.0083327194970355'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} ETH via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_RAINI,
        balance=Balance(amount=FVal(received_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} RAINI as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xdf0093104D66509B35411815d7b29c40C16c9578']])
def test_multiplex_batch_sell_token_for_eth(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xf9b40a3bbbd92fe72099cff45564e099782fc9b0b4bd40c2d87484b43735b3b1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1709306375000)
    swap_amount, received_amount, gas_fees = '13438.664993496960137988', '2.669421884825430502', '0.01627396521423088'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_LMWR,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} LMWR via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        balance=Balance(amount=FVal(received_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} ETH as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0xF6a17316821eD254EC0DFa270c6F9f0D3317f706']])
def test_multiplex_batch_sell_token_for_token(database, ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x0f422be6e6904700181c3effb0600a8ed7e1616e70e6587d383b29290d6a7c1d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1709300411000)
    swap_amount, received_amount, gas_fees = '125.156732374288853661', '43405.98545005', '0.018050672959219548'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_PRIME,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} PRIME via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_TSUKA,
        balance=Balance(amount=FVal(received_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} TSUKA as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x773E123A1F1d5495a8Eaf4556a9f4e8aFDd9989C']])
def test_0x415565b0_eth_to_token(database, ethereum_inquirer, ethereum_accounts):
    """Test ETH to Token swaps done through 0x415565b0 method ID via the 0x protocol router contract."""  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x56dd5341b27b744e3ef3a2f356a6db48cb811397495a4cb9e8924c8232ef9abc')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1709302619000)
    swap_amount, received_amount, gas_fees = '2.9077036701035723', '688264582.664559041869620658', '0.016733414171811015'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} ETH via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_SHIB,
        balance=Balance(amount=FVal(received_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} SHIB as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x61Ead4d3e373332c2099e2DC63F916Dbe99f4B0c']])
def test_0x415565b0_token_to_eth(database, ethereum_inquirer, ethereum_accounts):
    """Test Token to ETH swaps done through 0x415565b0 method ID via the 0x protocol router contract."""  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0xc4bab35f7499def296e9ccb08eebd8933ad8c37ff2701f2750027600f9050c55')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1709302223000)
    swap_amount, received_amount, gas_fees = '5000', '1.450387601635590055', '0.01419246270466794'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDC,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} USDC via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        balance=Balance(amount=FVal(received_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} ETH as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr()
@pytest.mark.parametrize('ethereum_accounts', [['0x85A28E964FCF12E0a6db44B3432794B08aD2426d']])
def test_0x415565b0_token_to_token(database, ethereum_inquirer, ethereum_accounts):
    """Test Token to Token swaps done through 0x415565b0 method ID via the 0x protocol router contract."""  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x29bd536ecd4cacec3495b02f6375ab7465be64fff015916484746cd18da7a37d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        database=database,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1709301911000)
    swap_amount, received_amount, gas_fees = '1496', '1480.467089', '0.014804818364279386'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        balance=Balance(amount=FVal(gas_fees)),
        location_label=ethereum_accounts[0],
        notes=f'Burned {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        balance=Balance(amount=FVal(swap_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} USDT via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDC,
        balance=Balance(amount=FVal(received_amount)),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} USDC as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events
