from typing import TYPE_CHECKING, Final

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.ethereum.modules.zerox.constants import ZEROX_ROUTER
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.cowswap.constants import CPT_COWSWAP
from rotkehlchen.chain.evm.decoding.zerox.constants import CPT_ZEROX
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.chain.optimism.modules.zerox.constants import ZEROX_ROUTER as OP_ZEROX_ROUTER
from rotkehlchen.constants.assets import A_ETH, A_OP, A_POLYGON_POS_MATIC, A_SNX, A_USDC, A_USDT
from rotkehlchen.constants.resolver import strethaddress_to_identifier
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.unit.decoders.test_aerodrome import A_AERO
from rotkehlchen.tests.unit.decoders.test_metamask import A_OPTIMISM_USDC
from rotkehlchen.tests.utils.constants import A_OPTIMISM_USDT
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.ethereum.node_inquirer import EthereumInquirer


A_AI: Final = Asset(strethaddress_to_identifier('0x2598c30330D5771AE9F983979209486aE26dE875'))
A_DRGN: Final = Asset(strethaddress_to_identifier('0x419c4dB4B9e25d6Db2AD9691ccb832C8D9fDA05E'))
A_MYRIA: Final = Asset(strethaddress_to_identifier('0xA0Ef786Bf476fE0810408CaBA05E536aC800ff86'))
A_LFG: Final = Asset(strethaddress_to_identifier('0x40a9A694197A0b4B92f2aAd48Da6bC1b6Ff194e9'))
A_BANANA: Final = Asset(strethaddress_to_identifier('0x38E68A37E401F7271568CecaAc63c6B1e19130B4'))
A_OXN: Final = Asset(strethaddress_to_identifier('0x9012744B7A564623b6C3E40b144fc196bdeDf1A9'))
A_RAINI: Final = Asset(strethaddress_to_identifier('0xeB953eDA0DC65e3246f43DC8fa13f35623bDd5eD'))
A_PRIME: Final = Asset(strethaddress_to_identifier('0xb23d80f5FefcDDaa212212F028021B41DEd428CF'))
A_TSUKA: Final = Asset(strethaddress_to_identifier('0xc5fB36dd2fb59d3B98dEfF88425a3F425Ee469eD'))
A_GF: Final = Asset(strethaddress_to_identifier('0xAaEf88cEa01475125522e117BFe45cF32044E238'))
A_SHIB: Final = Asset(strethaddress_to_identifier('0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE'))
A_LMWR: Final = Asset(strethaddress_to_identifier('0x628A3b2E302C7e896AcC432D2d0dD22B6cb9bc88'))
A_IXS: Final = Asset(strethaddress_to_identifier('0x73d7c860998CA3c01Ce8c808F5577d94d545d1b4'))
A_RLB: Final = Asset(strethaddress_to_identifier('0x046EeE2cc3188071C02BfC1745A6b17c656e3f3d'))
A_DERC: Final = Asset(strethaddress_to_identifier('0x9fa69536d1cda4A04cFB50688294de75B505a9aE'))
A_POLYGON_POS_USDT: Final = Asset('eip155:137/erc20:0xc2132D05D31c914a87C6611C10748AEb04B58e8F')
A_ARBITRUM_USDC: Final = Asset('eip155:42161/erc20:0xaf88d065e77c8cC2239327C5EDb3A432268e5831')
A_WSTETH: Final = Asset('eip155:42161/erc20:0x5979D7b546E38E414F7E9822514be443A4800529')
A_BASE_USDC: Final = Asset('eip155:8453/erc20:0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913')
A_USDE: Final = Asset(strethaddress_to_identifier('0x4c9EDD5852cd905f086C759E8383e09bff1E68B3'))
A_PENDLE: Final = Asset(strethaddress_to_identifier('0x808507121B80c02388fAd14726482e061B8da827'))
A_BULL: Final = Asset('eip155:137/erc20:0x9f95e17b2668AFE01F8fbD157068b0a4405Cc08D')


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xaE84961b9FA7412fEAEf209fD8f50C4F8Ef4D8fD']])
def test_sell_to_uniswap(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xb9827174e182a1b8df3507d13c5cedccdc974c4edd5d66f59355f7e9758b9006')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
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
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BANANA,
        amount=FVal(swap_amount),
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
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} OxN as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xc2aAd9386835C90deC9d669e35c128461E6102CA']])
def test_sell_eth_for_token_to_uniswap_v3(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x5b7719016f7d7d3d8ed9d4d86afd0e0079551d0a7795f70f01764ce5eaa44478')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
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
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(swap_amount),
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
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} MYRIA as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xed288d0261421C7cf36a56f23297cD5F4635A089']])
def test_sell_token_for_eth_to_uniswap_v3(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x68416e19252c678cdf67ae9b7adff742d78f95cea3c3f0582d3dc930340e5bdf')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
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
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_LFG,
        amount=FVal(swap_amount),
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
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} ETH as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xCCD54C835d7199ceEE2AedA4722C69eeeA6E606D']])
def test_sell_token_for_token_to_uniswap_v3(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6efe8a18de9ca3183bdb319be445f1b0b9041c0e8208fa04a58ee276b54574dd')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
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
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_AI,
        amount=FVal(swap_amount),
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
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} DRGN as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xddb143606305559e6b69843c1f53f2689D2aB605']])
def test_multiplex_batch_sell_eth_for_token(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xa151bc4f1c69591598386eaa65761cefd706cbfe0a1a340d8856dbfe2c3bd8c5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
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
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(swap_amount),
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
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} RAINI as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xdf0093104D66509B35411815d7b29c40C16c9578']])
def test_multiplex_batch_sell_token_for_eth(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xf9b40a3bbbd92fe72099cff45564e099782fc9b0b4bd40c2d87484b43735b3b1')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
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
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_LMWR,
        amount=FVal(swap_amount),
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
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} ETH as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xF6a17316821eD254EC0DFa270c6F9f0D3317f706']])
def test_multiplex_batch_sell_token_for_token(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x0f422be6e6904700181c3effb0600a8ed7e1616e70e6587d383b29290d6a7c1d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
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
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_PRIME,
        amount=FVal(swap_amount),
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
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} TSUKA as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xA5a81a7Bf4A737dAbCd8a4C5fc2A36598c1943bF']])
def test_multiplex_multihop_sell_token_for_token(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xceccb105d312df00105eca2560b8da4cd0e791bb0f0da4cebeb17ca46abf2ce4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1709652443000)
    swap_amount, received_amount, gas_fees = '64666', '143469.489576604990799103', '0.03327224673453317'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal(swap_amount),
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
        asset=A_GF,
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} GF as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x773E123A1F1d5495a8Eaf4556a9f4e8aFDd9989C']])
def test_0x415565b0_eth_to_token(ethereum_inquirer, ethereum_accounts):
    """Test ETH to Token swaps done through 0x415565b0 method ID via the 0x protocol router contract."""  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x56dd5341b27b744e3ef3a2f356a6db48cb811397495a4cb9e8924c8232ef9abc')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
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
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(swap_amount),
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
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} SHIB as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x61Ead4d3e373332c2099e2DC63F916Dbe99f4B0c']])
def test_0x415565b0_token_to_eth(ethereum_inquirer, ethereum_accounts):
    """Test Token to ETH swaps done through 0x415565b0 method ID via the 0x protocol router contract."""  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0xc4bab35f7499def296e9ccb08eebd8933ad8c37ff2701f2750027600f9050c55')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
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
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDC,
        amount=FVal(swap_amount),
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
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} ETH as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x85A28E964FCF12E0a6db44B3432794B08aD2426d']])
def test_0x415565b0_token_to_token(ethereum_inquirer, ethereum_accounts):
    """Test Token to Token swaps done through 0x415565b0 method ID via the 0x protocol router contract."""  # noqa: E501
    tx_hash = deserialize_evm_tx_hash('0x29bd536ecd4cacec3495b02f6375ab7465be64fff015916484746cd18da7a37d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
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
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal(swap_amount),
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
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} USDC as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xE4BeF064c912BC95C404850019909efe8D357716']])
def test_execute_meta_transaction_v2(ethereum_inquirer, ethereum_accounts):
    """Test meta transaction swaps done via the 0x protocol router contract."""
    tx_hash = deserialize_evm_tx_hash('0xb77f8e36a86517928f890296a263cafafa48ef01c6cc424a838b59b4401bf314')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1709638007000)
    swap_amount, received_amount, meta_tx_fees = '1405.596892', '4910.533168813496285354', '58.171192'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal(swap_amount),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} USDT via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_IXS,
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} IXS as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDT,
        amount=FVal(meta_tx_fees),
        location_label=ethereum_accounts[0],
        notes=f'Spend {meta_tx_fees} USDT as a 0x protocol fee',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x3951970BA92CBFff00496e8C5Ebd675cEB614773']])
def test_execute_meta_transaction_v2_multiplex(ethereum_inquirer, ethereum_accounts):
    """Test meta transaction multiplex swaps done via the 0x protocol router contract."""
    tx_hash = deserialize_evm_tx_hash('0x48f48d62b9829152c5963716acaed198320595859093cfc8a117742287f5a5eb')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1709641247000)
    swap_amount, received_amount, meta_tx_fees = '49934.597014', '352963.071479518181477885', '65.402986'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal(swap_amount),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} USDT via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_RLB,
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} RLB as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDT,
        amount=FVal(meta_tx_fees),
        location_label=ethereum_accounts[0],
        notes=f'Spend {meta_tx_fees} USDT as a 0x protocol fee',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x2dcd7947973cb5CBf20e3dBF0663F566D1De9CdA']])
def test_execute_meta_transaction_v2_flash(ethereum_inquirer, ethereum_accounts):
    """Test meta transaction swaps done via the 0x protocol using its flash contract."""
    tx_hash = deserialize_evm_tx_hash('0xf0be288974b275768725e7322c66d4086bd9b70bac4427af394966d333c0c807')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1709633675000)
    swap_amount, received_amount, meta_tx_fees = '10659.465069', '25162.301091908076364354', '60.028487'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal(swap_amount),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} USDT via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_DERC,
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} DERC as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDT,
        amount=FVal(meta_tx_fees),
        location_label=ethereum_accounts[0],
        notes=f'Spend {meta_tx_fees} USDT as a 0x protocol fee',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('polygon_pos_accounts', [['0x701D5a3344C98765b36014A8a71941f499A2Bc75']])
def test_swap_on_polygon_pos(polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash('0x8e7c52d519d1ca0d1dfd8c8c21a2d2c34574e2bdada0ae7faafd49c1ddb8e8a6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1709653684000)
    swap_amount, received_amount, gas_fees = '0.130848158787696777', '0.146129', '0.05669366828688572'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POLYGON_POS_MATIC,
        amount=FVal(gas_fees),
        location_label=polygon_pos_accounts[0],
        notes=f'Burn {gas_fees} POL for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_POLYGON_POS_MATIC,
        amount=FVal(swap_amount),
        location_label=polygon_pos_accounts[0],
        notes=f'Swap {swap_amount} POL via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_POLYGON_POS_USDT,
        amount=FVal(received_amount),
        location_label=polygon_pos_accounts[0],
        notes=f'Receive {received_amount} USDT as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xf06cc31757760CC9B8235C868ED90789f9c1E883']])
def test_swap_arbitrum_one(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x355c18ab70fb5d17098b6bc8fd527ce00f0b25c8220d6fe29522a1fb64b711bc')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1709664647000)
    swap_amount, received_amount, meta_tx_fees = '49920.273922', '11.88137754443033075', '79.726078'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ARBITRUM_USDC,
        amount=FVal(swap_amount),
        location_label=arbitrum_one_accounts[0],
        notes=f'Swap {swap_amount} USDC via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_WSTETH,
        amount=FVal(received_amount),
        location_label=arbitrum_one_accounts[0],
        notes=f'Receive {received_amount} wstETH as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ARBITRUM_USDC,
        amount=FVal(meta_tx_fees),
        location_label=arbitrum_one_accounts[0],
        notes=f'Spend {meta_tx_fees} USDC as a 0x protocol fee',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x4Ea754349AcE5303c82f0d1D491041e042f2ad22']])
def test_swap_optimism(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6b2b2d8c0cf2e27bb9e6c8309fd9887a066f9b72139acfe13d7ca5c29ae6c0ff')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1707868177000)
    swap_amount, received_amount, meta_tx_fees = '1.181244', '1.180785', '0.818756'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_OPTIMISM_USDC,
        amount=FVal(swap_amount),
        location_label=optimism_accounts[0],
        notes=f'Swap {swap_amount} USDC via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=OP_ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_OPTIMISM_USDT,
        amount=FVal(received_amount),
        location_label=optimism_accounts[0],
        notes=f'Receive {received_amount} USDT as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=OP_ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_OPTIMISM_USDC,
        amount=FVal(meta_tx_fees),
        location_label=optimism_accounts[0],
        notes=f'Spend {meta_tx_fees} USDC as a 0x protocol fee',
        counterparty=CPT_ZEROX,
        address=OP_ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('base_accounts', [['0xF68D2BfCecd7895BBa05a7451Dd09A1749026454']])
def test_swap_base(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0x4a5eb8fac7ef1d6637ff1d54e67791e4a5a49effb141f30e5af90f5aba5d48a5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=base_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1709665909000)
    swap_amount, received_amount, meta_tx_fees = '688.271588', '1726.46678822133419734', '4.288419'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BASE_USDC,
        amount=FVal(swap_amount),
        location_label=base_accounts[0],
        notes=f'Swap {swap_amount} USDC via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_AERO,
        amount=FVal(received_amount),
        location_label=base_accounts[0],
        notes=f'Receive {received_amount} AERO as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BASE_USDC,
        amount=FVal(meta_tx_fees),
        location_label=base_accounts[0],
        notes=f'Spend {meta_tx_fees} USDC as a 0x protocol fee',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xA26B29a299c65D0F63A8568BA5663028347f5571']])
def test_swap_on_pancakeswap(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xcfb3b1587bb4d24a06d0f543493098ab285ae3763a489911da5bbea99bcb3499')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1709701415000)
    swap_amount, received_amount, gas_fees = '10.414111669423209', '36912.012249', '0.017837784148433769'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(swap_amount),
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
        asset=A_USDT,
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} USDT as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x74882149e6a43b8E69cAC6Aef92D753e96054B78']])
def test_swap_on_curve(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x12d794e7ced93da02978aa9b46b59f27ceab49724fdb1b0c39963792af68fdf0')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1709683307000)
    swap_amount, received_amount, gas_fees = '458480.413', '459177.562744', '0.03000569702410494'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDE,
        amount=FVal(swap_amount),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} USDe via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDT,
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} USDT as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xfD1F67fDbA4F0C1952861345237463b39228F1C6']])
def test_swap_on_sushiswap(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x802f7d1c4b2f1b7ef48e5c3af92a3a166a91624b89e736f85b90df3dd7ce9d73')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1708569407000)
    swap_amount, received_amount, gas_fees = '50', '68.557872437267381014', '0.007767959110971294'
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=ethereum_accounts[0],
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_SNX,
        amount=FVal(swap_amount),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} SNX via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_PENDLE,
        amount=FVal(received_amount),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} PENDLE as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('polygon_pos_accounts', [['0xb3Dd5Cdb7F73acD1177c96409412e0b326E9C457']])
def test_swap_on_quickswap(polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash('0x7b1bef89b8890e060787924a279e040ce8d50aedd35337747af6d56024ce269e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1709675020000)
    swap_amount, received_amount, gas_fees = '58.6229436575138', '10313.421767180867447506', '0.05297558472'  # noqa: E501
    expected_events = [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POLYGON_POS_MATIC,
        amount=FVal(gas_fees),
        location_label=polygon_pos_accounts[0],
        notes=f'Burn {gas_fees} POL for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_POLYGON_POS_MATIC,
        amount=FVal(swap_amount),
        location_label=polygon_pos_accounts[0],
        notes=f'Swap {swap_amount} POL via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_BULL,
        amount=FVal(received_amount),
        location_label=polygon_pos_accounts[0],
        notes=f'Receive {received_amount} BULL as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=ZEROX_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('optimism_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_swap_optimism_with_return(optimism_inquirer, optimism_accounts):
    """Check that a swap with an amount returned is decoded correctly.
    Regression test for https://github.com/rotki/rotki/issues/9122
    """
    tx_hash = deserialize_evm_tx_hash('0x0745615163e01c8a446f2520d5fa008dd69f308f24bcc3d2fec2466c1a2bc25c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=optimism_inquirer, tx_hash=tx_hash)
    user_address, timestamp, gas_amount, swap_amount, received_amount = optimism_accounts[0], TimestampMS(1706654255000), '0.000527795236079617', '1813.728944336150781643', '5820.310306'  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.OPTIMISM,
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
        location=Location.OPTIMISM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_OP,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} OP via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=OP_ZEROX_ROUTER,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607'),
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} USDC.e as the result of a swap via the 0x protocol',
        counterparty=CPT_ZEROX,
        address=OP_ZEROX_ROUTER,
    )]


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x43F9A40200310CE535EdF5EA0eb71afB53779BA4']])
def test_swap_anon_event(ethereum_inquirer: 'EthereumInquirer', ethereum_accounts):
    """zerox has a special contract for swaps that emits an anonymous event that causes the
    logic of some post decoding rules to fail. This is a regression test for this contract.
    """
    tx_hash = deserialize_evm_tx_hash('0x5871cd5d19d749135ac563eddb4cb04bd0d13f05414666a887b1628f5968b7dc')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1733427911000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0x58D97B57BB95320F9a05dC918Aef65434969c2B2'),
        amount=FVal(swap_amount := '7720.393471610974409838'),
        location_label=ethereum_accounts[0],
        notes=f'Swap {swap_amount} MORPHO in a cowswap twap order',
        counterparty=CPT_COWSWAP,
        address=(address := string_to_evm_address('0x9008D19f58AAbD9eD0D60971565AA8510560ab41')),
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),
        amount=FVal(received_amount := '17631.876781'),
        location_label=ethereum_accounts[0],
        notes=f'Receive {received_amount} USDC as the result of a cowswap twap order',
        counterparty=CPT_COWSWAP,
        address=address,
    ), EvmEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=Asset('eip155:1/erc20:0x58D97B57BB95320F9a05dC918Aef65434969c2B2'),
        amount=FVal(fee_amount := '14.050054845407416491'),
        location_label=ethereum_accounts[0],
        notes=f'Spend {fee_amount} MORPHO as a cowswap fee',
        counterparty=CPT_COWSWAP,
        address=address,
    )]
