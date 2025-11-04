from typing import TYPE_CHECKING, Final

import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.base.modules.paraswap.v5.constants import (
    PARASWAP_AUGUSTUS_ROUTER as PARASWAP_AUGUSTUS_ROUTER_BASE,
)
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.paraswap.v5.constants import PARASWAP_AUGUSTUS_ROUTER
from rotkehlchen.chain.evm.decoding.paraswap.constants import CPT_PARASWAP
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import (
    A_BSC_BNB,
    A_ENS,
    A_ETH,
    A_KP3R,
    A_LINK,
    A_POL,
    A_SUSHI,
    A_USDC,
    A_USDT,
    A_WBTC,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.constants import A_OPTIMISM_USDT
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

if TYPE_CHECKING:
    from rotkehlchen.chain.binance_sc.node_inquirer import BinanceSCInquirer
    from rotkehlchen.types import ChecksumEvmAddress

A_PSP = Asset('eip155:1/erc20:0xcAfE001067cDEF266AfB7Eb5A286dCFD277f3dE5')
A_ROUTE = Asset('eip155:1/erc20:0x16ECCfDbb4eE1A85A33f3A9B21175Cd7Ae753dB4')
A_stETH = Asset('eip155:1/erc20:0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84')
A_MPL = Asset('eip155:1/erc20:0x33349B282065b0284d756F0577FB39c158F935e6')
A_TKST = Asset('eip155:1/erc20:0x7CdBfC86A0BFa20F133748B0CF5cEa5b787b182c')
A_PRISMA = Asset('eip155:1/erc20:0xdA47862a83dac0c112BA89c6abC2159b95afd71C')
A_UDOODLE = Asset('eip155:1/erc20:0xa07dCC1aBFe20D29D87a32E2bA89876145DAfB0a')
A_AUCTION = Asset('eip155:1/erc20:0xA9B1Eb5908CfC3cdf91F9B8B3a74108598009096')
A_FXS = Asset('eip155:1/erc20:0x3432B6A60D23Ca0dFCa7761B7ab56459D9C964D0')
A_cvxFXS = Asset('eip155:1/erc20:0xFEEf77d3f69374f66429C91d732A244f074bdf74')
A_BRIDGED_USDC = Asset('eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8')
A_cbETH = Asset('eip155:8453/erc20:0x2Ae3F1Ec7F1F5012CFEab0185bfc7aa3cf0DEc22')
A_sUSD = Asset('eip155:10/erc20:0x8c6f28f2F1A3C87F0f938b96d27520d9751ec8d9')
A_POLYGON_POS_USDC = Asset('eip155:137/erc20:0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359')
A_POLYGON_POS_DAI = Asset('eip155:137/erc20:0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063')


PARASWAP_TOKEN_TRANSFER_PROXY: Final = string_to_evm_address('0x216B4B4Ba9F3e719726886d34a177484278Bfcae')  # noqa: E501


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xf8fa0bB0798489445577fA7387dcB2125C361c28']])
def test_simple_swap_no_fee(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xeab04bca5abb6a794fd83e3c336b128824a2d3a72abf565d82a6ecd39d5929ef')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704814775000)
    swap_amount, received_amount, approval_amount, gas_fees = '3860.977240111926214656', '3997.851328', '115792089237316195423570985008687907853269984665640564034996.606767801203425279', '0.003865522700588692'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=296,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_SUSHI,
        amount=FVal(approval_amount),
        location_label=user_address,
        notes=f'Set SUSHI spending approval of {user_address} by {PARASWAP_TOKEN_TRANSFER_PROXY} to {approval_amount}',  # noqa: E501
        counterparty=None,
        address=PARASWAP_TOKEN_TRANSFER_PROXY,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=297,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_SUSHI,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} SUSHI in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=298,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDT,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} USDT as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x711ee578860F6f621401A6148b09F69c1F8508B2']])
def test_simple_swap_eth_fee(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xeeea20b39f157fe59fa4904fd4b62f8971188b53d05c6831e0ed67ee157e40c2')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704806231000)
    swap_amount, received_amount, gas_fees, paraswap_fee = '3.020129914302378395', '3.019113864780728103', '0.00680806307180382', '0.028681581715416916'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_stETH,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} stETH in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} ETH as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(paraswap_fee),
        location_label=user_address,
        notes=f'Spend {paraswap_fee} ETH as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xd3669637F3C520d73eE922EA62D2C33F547F9Cd6']])
def test_simple_swap_token_fee(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xf4d28d1c46dde983fac73db8e651514fe7299edaf40870766462362b1b1a1d83')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704797495000)
    swap_amount, received_amount, gas_fees, paraswap_fee = '138.2851', '1190.359719', '0.0034595', '11.308417'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_ROUTE,
        amount=ZERO,
        location_label=user_address,
        notes=f'Revoke ROUTE spending approval of {user_address} by {PARASWAP_TOKEN_TRANSFER_PROXY}',  # noqa: E501
        counterparty=None,
        address=PARASWAP_TOKEN_TRANSFER_PROXY,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ROUTE,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} ROUTE in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDC,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} USDC as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=4,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDC,
        amount=FVal(paraswap_fee),
        location_label=user_address,
        notes=f'Spend {paraswap_fee} USDC as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xf84C3222D213e53a053A97E426738Cb12c50CBA5']])
def test_simple_buy(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x695739b3eab8dc7e6ef7f9b362983cfd4d9b81592b0840bd0ca69b0b2e8e51f9')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704888587000)
    swap_amount, received_amount, gas_fees = '223.031074350165285613', '200.000000000000000001', '0.00727228725913224'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_LINK,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} LINK in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ENS,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} ENS as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x33e543cB6Be7b33fF95FAF61eA8106b384E74912']])
def test_multi_swap_no_fee(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6f7313845874cb26cda5d63adcbf9899edf257f2e196a7ace641bdbb179947e7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704815411000)
    swap_amount, received_amount, gas_fees = '400', '30.498415074803766847', '0.007613212553923857'
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} USDT in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_MPL,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} MPL as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xBc067f00652Ba0B3278a3d373431769F2805Bc27']])
def test_multi_swap_token_fee(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x0c55b3df325d145b82fbe4e135e88eeae9820b035842b2ec5e17ccb1357375c6')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704883367000)
    swap_amount, received_amount, gas_fees, paraswap_fee = '24996', '48398.029944956021622964', '0.010829082710902124', '91.956256895416441083'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} USDT in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_TKST,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} TKST as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_TKST,
        amount=FVal(paraswap_fee),
        location_label=user_address,
        notes=f'Spend {paraswap_fee} TKST as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x4e9B2f2B72F6A5B3735cD18357F0F0EF950D1Ba7']])
def test_mega_swap_no_fee(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x5c36bcfa67d3306a3fe21203b7279e589d26c9925d055b3174ac259b262345f3')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704802211000)
    swap_amount, received_amount, gas_fees = '219410.681102', '4.68800235', '0.019375015240876558'
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=12,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_USDC,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Set USDC spending approval of {user_address} by {PARASWAP_TOKEN_TRANSFER_PROXY} to {swap_amount}',  # noqa: E501
        counterparty=None,
        address=PARASWAP_TOKEN_TRANSFER_PROXY,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=13,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDC,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} USDC in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=14,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_WBTC,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} WBTC as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x752921eAead738CFd1aEB8571a58480dB51e42C1']])
def test_mega_swap_token_fee(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x9c529e46976ce23d1caf3dc1c062ee3c9ec9c327014f5447761409788e842294')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704881183000)
    swap_amount, received_amount, gas_fees, paraswap_fee = '42226.901446319896728285', '40567.774843', '0.028635611789064984', '0.858994'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_PRISMA,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} PRISMA in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDC,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} USDC as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_USDC,
        amount=FVal(paraswap_fee),
        location_label=user_address,
        notes=f'Spend {paraswap_fee} USDC as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xe952e50D1F82bBfb5054311Ca689807e343a1ab8']])
def test_swap_on_uniswap_v2_fork(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x6fa4a6a9c0d9c5aad831cc1ff149fb7683c0573db93571bc43acb5b4848314ae')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704889739000)
    swap_amount, received_amount, gas_fees = '0.35', '835.81811', '0.00296189763180853'
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} ETH in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDC,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} USDC as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x4AE269b8e9116f8E44797D7424E8351286FCDfab']])
def test_swap_on_uniswap_v2_fork_with_permit(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xaab04d564e1f065b350e6aa6fda9d0ff51082e8810520e691866fdade91ba9c4')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704889595000)
    swap_amount, received_amount, approval_amount, gas_fees = '150', '150.152117', '115792089237316195423570985008687907853269984665640564039457584007913129.639935', '0.004565275677196416'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=102,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_USDC,
        amount=FVal(approval_amount),
        location_label=user_address,
        notes=f'Set USDC spending approval of {user_address} by {PARASWAP_TOKEN_TRANSFER_PROXY} to {approval_amount}',  # noqa: E501
        counterparty=None,
        address=PARASWAP_TOKEN_TRANSFER_PROXY,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=103,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDC,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} USDC in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=104,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDT,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} USDT as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xA80F8ac7Fe79558854E26A49867D11f8cF9cC36B']])
def test_buy_uniswap_v2_fork(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x15df127374a04772df72b94685f60f71200da679e4bc2c334a12889fe2ab046c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1705575743000)
    swap_amount, received_amount, gas_fees = '0.396919294295211225', '40', '0.004393070468277507'
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} ETH in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_AUCTION,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} AUCTION as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xB855c4eBb5b6eB3F2033aecC4E543e27BC39465D']])
def test_direct_uniswap_v3_swap(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2b6e830d4b32c22b3c4c2a26dbdb9a17c3cc2962fc35d5b4cd5d56c58cbec68a')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1704888899000)
    swap_amount, received_amount, gas_fees = '2010000', '3.265498018938813939', '0.005934293486927232'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_UDOODLE,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} μDOODLE in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} ETH as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xE93EB339C3d826F8A4d14Cc14CA008375915000F']])
def test_direct_curve_v1_swap(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x5a601f524592627eaf3562e4cb1340880260a1bf627a984392308cdf79a828dc')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1705577795000)
    swap_amount, received_amount, gas_fees = '1175.108', '1343.06000017590196878', '0.008673416651691594'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=96,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_FXS,
        amount=ZERO,
        location_label=user_address,
        notes=f'Revoke FXS spending approval of {user_address} by {PARASWAP_TOKEN_TRANSFER_PROXY}',
        counterparty=None,
        address=PARASWAP_TOKEN_TRANSFER_PROXY,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=97,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_FXS,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} FXS in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=98,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_cvxFXS,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} cvxFXS as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x6133de401FB609aACB767D8b379157731a09b66b']])
def test_direct_curve_v2_swap(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x2ea92952050e9f5cbf9b46619355a3b34822286443e10a6f5405573330def118')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1705502243000)
    swap_amount, received_amount, gas_fees = '5.48189', '184.099593744496046878', '0.01392159540206184'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} ETH in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_KP3R,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} KP3R as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x23a49A9930f5b562c6B1096C3e6b5BEc133E8B2E']])
def test_direct_balancer_v2_given_swap(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x606413e4074e79e68ee0f79eee96c94cf091e7c061a551d2dd2a27044fb007e7')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1705575743000)
    swap_amount, received_amount, gas_fees = '17438.484493735105063894', '0.253269184972671572', '0.006247513881593877'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=242,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_PSP,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Set PSP spending approval of {user_address} by {PARASWAP_TOKEN_TRANSFER_PROXY} to {swap_amount}',  # noqa: E501
        counterparty=None,
        address=PARASWAP_TOKEN_TRANSFER_PROXY,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=243,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_PSP,
        amount=ZERO,
        location_label=user_address,
        notes=f'Revoke PSP spending approval of {user_address} by {PARASWAP_TOKEN_TRANSFER_PROXY}',
        counterparty=None,
        address=PARASWAP_TOKEN_TRANSFER_PROXY,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=244,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_PSP,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} PSP in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=245,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} ETH as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('arbitrum_one_accounts', [['0xFee285cf79719FC3552c5F7c540554f09DAdAD21']])
def test_simple_buy_fee_arbitrum_one(arbitrum_one_inquirer, arbitrum_one_accounts):
    tx_hash = deserialize_evm_tx_hash('0x92a422b746cc1ce14b795e5fc2239cdf3146482a5bc3c5278dccb1c3ccccdc17')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=arbitrum_one_inquirer,
        tx_hash=tx_hash,
    )
    user_address = arbitrum_one_accounts[0]
    timestamp = TimestampMS(1705593327000)
    swap_amount, received_amount, approval_amount, gas_fees, paraswap_fee = '0.145421', '0.000057531692024488', '15.547876', '0.0002783844', '0.000002'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=25,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_BRIDGED_USDC,
        amount=FVal(approval_amount),
        location_label=user_address,
        notes=f'Set USDC.e spending approval of {user_address} by {PARASWAP_TOKEN_TRANSFER_PROXY} to {approval_amount}',  # noqa: E501
        counterparty=None,
        address=PARASWAP_TOKEN_TRANSFER_PROXY,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=26,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_BRIDGED_USDC,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} USDC.e in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=27,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} ETH as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=28,
        timestamp=timestamp,
        location=Location.ARBITRUM_ONE,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_BRIDGED_USDC,
        amount=FVal(paraswap_fee),
        location_label=user_address,
        notes=f'Spend {paraswap_fee} USDC.e as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('base_accounts', [['0x66CF237A0D3505E80eF083E0F8D4Cad09Fd0BFe4']])
def test_simple_swap_no_fee_base(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0xf93a7211656753e841899b40edf3a9ccfded6b40b6d7b3538a4215362f9bd34f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_inquirer,
        tx_hash=tx_hash,
    )
    user_address = base_accounts[0]
    timestamp = TimestampMS(1705604855000)
    swap_amount, received_amount, gas_fees = '0.051094010416535325', '0.048393744103758202', '0.000257848719493097'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.BASE,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.BASE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} ETH in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER_BASE,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.BASE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_cbETH,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} cbETH as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER_BASE,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0xDa2181fB19f2Fe365BeF6Ccb84209d6FDb0d1828']])
def test_direct_curve_v1_swap_optimism(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0x83ac5abc6819fca458f614e4fdbca6fe324bbea8b7ce5fb072bf99407cd8c031')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        tx_hash=tx_hash,
    )
    user_address = optimism_accounts[0]
    timestamp = TimestampMS(1705666455000)
    swap_amount, received_amount, paraswap_fee, gas_fees = '16000.007289', '16026.407272974863067802', '0.262301326491870034', '0.000098575498010565'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=13,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_OPTIMISM_USDT,
        amount=ZERO,
        location_label=user_address,
        notes=f'Revoke USDT spending approval of {user_address} by {PARASWAP_TOKEN_TRANSFER_PROXY}',  # noqa: E501
        counterparty=None,
        address=PARASWAP_TOKEN_TRANSFER_PROXY,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=14,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_OPTIMISM_USDT,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} USDT in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=15,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_sUSD,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} sUSD as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=16,
        timestamp=timestamp,
        location=Location.OPTIMISM,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_sUSD,
        amount=FVal(paraswap_fee),
        location_label=user_address,
        notes=f'Spend {paraswap_fee} sUSD as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('polygon_pos_accounts', [['0xe03679B59AC0026036ba4518bc0d5e5F800Bd9c1']])
def test_direct_uniswap_v3_swap_polygon(polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash('0x4f72cff63802c8eed51662e3d1e20bc7e86ac06cdc1aa490c26cfeee075b6018')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    user_address = polygon_pos_accounts[0]
    timestamp = TimestampMS(1705665114000)
    swap_amount, received_amount, paraswap_fee, gas_fees = '4', '3.999618836617901732', '0.000000000000000002', '0.010937453116939734'  # noqa: E501
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POL,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} POL for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_POLYGON_POS_USDC,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} USDC in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_POLYGON_POS_DAI,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} DAI as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.POLYGON_POS,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_POLYGON_POS_DAI,
        amount=FVal(paraswap_fee),
        location_label=user_address,
        notes=f'Spend {paraswap_fee} DAI as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x60A543647a1ecAccAADFc2DF27a2D1D74e60A39f']])
def test_paraswap_fork_with_factory(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x90d9e615e808d5d9b62f6f072c783e9a9f8417c46fcc6665a4aadd927dc74fce')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)

    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1646086826000)
    swap_amount, received_amount, gas_fees = '7800', '0.338822187329295101', '0.010252494'
    expected_events = [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_fees),
        location_label=user_address,
        notes=f'Burn {gas_fees} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=201,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=A_PSP,
        amount=ZERO,
        location_label=user_address,
        notes=f'Revoke PSP spending approval of {user_address} by 0x216B4B4Ba9F3e719726886d34a177484278Bfcae',  # noqa: E501
        address='0x216B4B4Ba9F3e719726886d34a177484278Bfcae',
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=202,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_PSP,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} PSP in paraswap',
        counterparty=CPT_PARASWAP,
        address='0xDEF171Fe48CF0115B1d80b88dc8eAB59176FEe57',
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=203,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} ETH as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address='0xDEF171Fe48CF0115B1d80b88dc8eAB59176FEe57',
    )]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('binance_sc_accounts', [['0x92dD70347F1f7F9Feb3385131e0C875D96c5269e']])
def test_multi_swap_token_fee_binance_sc(
        binance_sc_inquirer: 'BinanceSCInquirer',
        binance_sc_accounts: list['ChecksumEvmAddress'],
) -> None:
    tx_hash = deserialize_evm_tx_hash('0xdbad52c68bd2d736ad38560cab087785086c3e86ab4b685251cba9898639a592')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=binance_sc_inquirer, tx_hash=tx_hash)  # noqa: E501
    user_address, timestamp = binance_sc_accounts[0], TimestampMS(1736461652000)
    gas_amount, swap_amount, received_amount, fee_amount, approve_amount = '0.000686569', '25', '898.294085817726117778', '8.533793815268398118', '115792089237316195423570985008687907853269984665640564039432.584007913129639935'  # noqa: E501
    a_bsc_avax, a_bsc_usdc = Asset('eip155:56/erc20:0x1CE0c2827e2eF14D5C4f29a091d735A204794041'), Asset('eip155:56/erc20:0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d')  # noqa: E501
    assert events == [EvmEvent(
        tx_ref=tx_hash,
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
    ), EvmEvent(
        tx_ref=tx_hash,
        sequence_index=273,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_type=HistoryEventType.INFORMATIONAL,
        event_subtype=HistoryEventSubType.APPROVE,
        asset=a_bsc_avax,
        amount=FVal(approve_amount),
        location_label=user_address,
        notes=f'Set AVAX spending approval of {user_address} by 0x216B4B4Ba9F3e719726886d34a177484278Bfcae to {approve_amount}',  # noqa: E501
        address=string_to_evm_address('0x216B4B4Ba9F3e719726886d34a177484278Bfcae'),
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=274,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.SPEND,
        asset=a_bsc_avax,
        amount=FVal(swap_amount),
        location_label=user_address,
        notes=f'Swap {swap_amount} AVAX in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=275,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=a_bsc_usdc,
        amount=FVal(received_amount),
        location_label=user_address,
        notes=f'Receive {received_amount} USDC as the result of a swap in paraswap',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=276,
        timestamp=timestamp,
        location=Location.BINANCE_SC,
        event_subtype=HistoryEventSubType.FEE,
        asset=a_bsc_usdc,
        amount=FVal(fee_amount),
        location_label=user_address,
        notes=f'Spend {fee_amount} USDC as a paraswap fee',
        counterparty=CPT_PARASWAP,
        address=PARASWAP_AUGUSTUS_ROUTER,
    )]
