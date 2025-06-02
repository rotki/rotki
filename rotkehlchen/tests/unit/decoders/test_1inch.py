import pytest

from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.chain.ethereum.modules.oneinch.constants import (
    CPT_ONEINCH_V1,
    CPT_ONEINCH_V2,
    CPT_ONEINCH_V3,
    CPT_ONEINCH_V4,
    CPT_ONEINCH_V5,
)
from rotkehlchen.chain.ethereum.modules.oneinch.v2.constants import ONEINCH_V2_MAINNET_ROUTER
from rotkehlchen.chain.ethereum.modules.oneinch.v3.constants import ONEINCH_V3_MAINNET_ROUTER
from rotkehlchen.chain.evm.decoding.constants import CPT_GAS
from rotkehlchen.chain.evm.decoding.oneinch.constants import CPT_ONEINCH_V6, ONEINCH_V6_ROUTER
from rotkehlchen.chain.evm.decoding.oneinch.v4.constants import ONEINCH_V4_ROUTER
from rotkehlchen.chain.evm.decoding.oneinch.v5.decoder import ONEINCH_V5_ROUTER
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import (
    A_CRV,
    A_DAI,
    A_ETH,
    A_LUSD,
    A_POLYGON_POS_MATIC,
    A_USDC,
    A_USDT,
    A_WETH,
    A_XDAI,
)
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.constants import A_CHI, A_PAN
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash

ADDY = '0x2B888954421b424C5D3D9Ce9bB67c9bD47537d12'


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_1inchv1_swap(ethereum_inquirer):
    """Data taken from
    https://etherscan.io/tx/0x8b8652c502e80ce7c5441cdedc9184ea8f07a9c13b4c3446a47ae08c6c1d6efa
    """
    tx_hash = deserialize_evm_tx_hash('0x8b8652c502e80ce7c5441cdedc9184ea8f07a9c13b4c3446a47ae08c6c1d6efa')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    chispender_addy = string_to_evm_address('0xed04A060050cc289d91779A8BB3942C3A6589254')
    oneinch_contract = string_to_evm_address('0x11111254369792b2Ca5d084aB5eEA397cA8fa48B')
    timestamp = TimestampMS(1594500575000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00896373909'),
            location_label=ADDY,
            notes='Burn 0.00896373909 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=103,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_CHI,
            amount=ZERO,
            location_label=ADDY,
            notes=f'Revoke CHI spending approval of {ADDY} by {chispender_addy}',
            address=chispender_addy,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=104,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            amount=FVal('138.75'),
            location_label=ADDY,
            notes=f'Swap 138.75 USDC in {CPT_ONEINCH_V1} from {ADDY}',
            counterparty=CPT_ONEINCH_V1,
            address=oneinch_contract,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=105,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_DAI,
            amount=FVal('135.959878392183347402'),
            location_label=ADDY,
            notes=f'Receive 135.959878392183347402 DAI from 1inch-v1 swap in {ADDY}',
            counterparty=CPT_ONEINCH_V1,
            address=oneinch_contract,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [[ADDY]])
def test_1inchv2_swap_for_eth(ethereum_inquirer):
    """
    Test an 1inchv2 swap for ETH.

    Data taken from
    https://etherscan.io/tx/0x5edc23d5a05e347afc60e64a4d5831ed2551985c21dceb85d267926ca2e2c13e
    """
    tx_hash = deserialize_evm_tx_hash('0x5edc23d5a05e347afc60e64a4d5831ed2551985c21dceb85d267926ca2e2c13e')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1608498702000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.002618947'),
            location_label=ADDY,
            notes='Burn 0.002618947 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=218,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_PAN,
            amount=FVal('115792089237316195423570985008687907853269984665640564037304.954007913129639935'),
            location_label=ADDY,
            notes=f'Set PAN spending approval of {ADDY} by {ONEINCH_V2_MAINNET_ROUTER} to 115792089237316195423570985008687907853269984665640564037304.954007913129639935',  # noqa: E501
            address=ONEINCH_V2_MAINNET_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=219,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_PAN,
            amount=FVal('2152.63'),
            location_label=ADDY,
            notes='Swap 2152.63 PAN in 1inch-v2',
            counterparty=CPT_ONEINCH_V2,
            address=ONEINCH_V2_MAINNET_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=220,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('0.220582251767407014'),
            location_label=ADDY,
            notes='Receive 0.220582251767407014 ETH from 1inch-v2 swap',
            counterparty=CPT_ONEINCH_V2,
            address=ONEINCH_V2_MAINNET_ROUTER,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_1inchv3_swap_for_eth(ethereum_inquirer, ethereum_accounts):
    """Test an 1inchv3 swap for ETH."""
    tx_hash = deserialize_evm_tx_hash('0xc9403f8010c78cec3036fd502103b78566f9b50eae57068538735527b59435ae')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    user_address = ethereum_accounts[0]
    timestamp = TimestampMS(1618011137000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.0103897731'),
            location_label=user_address,
            notes='Burn 0.0103897731 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            amount=FVal('263.425'),
            location_label=user_address,
            notes='Swap 263.425 USDT in 1inch-v3',
            counterparty=CPT_ONEINCH_V3,
            address=ONEINCH_V3_MAINNET_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('0.127775213950949157'),
            location_label=user_address,
            notes='Receive 0.127775213950949157 ETH as a result of a 1inch-v3 swap',
            counterparty=CPT_ONEINCH_V3,
            address=ONEINCH_V3_MAINNET_ROUTER,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x312419eEC9C4632155904D9440dc1EeeafFBb280']])
def test_1inchv4_swap_on_uniswapv3(ethereum_inquirer):
    """
    Test an 1inch v4 swap for ETH via Uniswap v3.

    Data taken from
    https://etherscan.io/tx/0xd02bbee01f92d778af8c2d159fb269ad31425b32703da568abb427ac14547e6d
    """
    tx_hash = deserialize_evm_tx_hash('0xd02bbee01f92d778af8c2d159fb269ad31425b32703da568abb427ac14547e6d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp = TimestampMS(1687361999000)
    user_address = '0x312419eEC9C4632155904D9440dc1EeeafFBb280'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.005753512813468296'),
            location_label=user_address,
            notes='Burn 0.005753512813468296 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            amount=FVal('5527'),
            location_label=user_address,
            notes=f'Swap 5527 USDT in {CPT_ONEINCH_V4}',
            address=ONEINCH_V4_ROUTER,
            counterparty=CPT_ONEINCH_V4,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('2.930675563626228657'),
            location_label=user_address,
            notes=f'Receive 2.930675563626228657 ETH as a result of a {CPT_ONEINCH_V4} swap',
            address=ONEINCH_V4_ROUTER,
            counterparty=CPT_ONEINCH_V4,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x456325F2AC7067234dD71E01bebe032B0255e039']])
def test_1inchv4_orderfilledrfq(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0x7e98fc61cdec43a7b886a9d045264bcc9292b2a34f8c466e4270ee6671684b69')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, user_address, gas, amount_out, amount_in = TimestampMS(1683201803000), ethereum_accounts[0], '0.010777074', '1457.408044', '634.912997630527012864'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=user_address,
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDT,
            amount=FVal(amount_out),
            location_label=user_address,
            notes=f'Swap {amount_out} USDT in {CPT_ONEINCH_V4}',
            address=ONEINCH_V4_ROUTER,
            counterparty=CPT_ONEINCH_V4,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=EvmToken('eip155:1/erc20:0x6De037ef9aD2725EB40118Bb1702EBb27e4Aeb24'),
            amount=FVal(amount_in),
            location_label=user_address,
            notes=f'Receive {amount_in} RNDR as a result of a {CPT_ONEINCH_V4} swap',
            address=ONEINCH_V4_ROUTER,
            counterparty=CPT_ONEINCH_V4,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xF92940216a808378bfFD05f444B7bF71d5A193Cd']])
def test_1inchv4_swap_on_sushiswap(ethereum_inquirer):
    """
    Test an 1inch v4 swap for ETH via Sushiswap.

    Data taken from
    https://etherscan.io/tx/0x396f57534e5deff9b530357bda8dcd31b80892ba7ce3de6f6593b0225bba3d0f
    """
    tx_hash = deserialize_evm_tx_hash('0x396f57534e5deff9b530357bda8dcd31b80892ba7ce3de6f6593b0225bba3d0f')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1687551611000)
    user_address = '0xF92940216a808378bfFD05f444B7bF71d5A193Cd'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.003337072472716185'),
            location_label=user_address,
            notes='Burn 0.003337072472716185 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_USDC,
            amount=FVal('121.424518'),
            location_label=user_address,
            notes=f'Swap 121.424518 USDC in {CPT_ONEINCH_V4}',
            address=ONEINCH_V4_ROUTER,
            counterparty=CPT_ONEINCH_V4,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('0.062555211026786486'),
            location_label=user_address,
            notes=f'Receive 0.062555211026786486 ETH as a result of a {CPT_ONEINCH_V4} swap',
            address=ONEINCH_V4_ROUTER,
            counterparty=CPT_ONEINCH_V4,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0x201b5Abfd44A8F9b75F0fE1BaE74CDaC7675E54B']])
def test_1inchv4_multiple_swaps(ethereum_inquirer):
    """
    Test an 1inch v4 swap via multiple pools.

    Data taken from
    https://etherscan.io/tx/0xeeefe25741462f0832183925ac4b1b840b819fbacd95cfc635496d853b7022bd
    """
    tx_hash = deserialize_evm_tx_hash('0xeeefe25741462f0832183925ac4b1b840b819fbacd95cfc635496d853b7022bd')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1687762727000)
    user_address = '0x201b5Abfd44A8F9b75F0fE1BaE74CDaC7675E54B'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.007395128691813344'),
            location_label=user_address,
            notes='Burn 0.007395128691813344 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=34,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:1/erc20:0xE60779CC1b2c1d0580611c526a8DF0E3f870EC48'),
            amount=FVal('115792089237316195423570985008687907853269984665640563937640.413716264772814197'),
            location_label=user_address,
            notes=f'Set USH spending approval of {user_address} by {ONEINCH_V4_ROUTER} to 115792089237316195423570985008687907853269984665640563937640.413716264772814197',  # noqa: E501
            address=ONEINCH_V4_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=35,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:1/erc20:0xE60779CC1b2c1d0580611c526a8DF0E3f870EC48'),
            amount=FVal('50000'),
            location_label=user_address,
            notes=f'Swap 50000 USH in {CPT_ONEINCH_V4}',
            address=ONEINCH_V4_ROUTER,
            counterparty=CPT_ONEINCH_V4,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=36,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_USDC,
            amount=FVal('7003.996145'),
            location_label=user_address,
            notes=f'Receive 7003.996145 USDC as a result of a {CPT_ONEINCH_V4} swap',
            address=ONEINCH_V4_ROUTER,
            counterparty=CPT_ONEINCH_V4,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xcA74F404E0C7bfA35B13B511097df966D5a65597']])
def test_1inchv4_weth_eth_swap(ethereum_inquirer):
    """
    Test an 1inch v4 WETH to ETH swap via the WETH contract.

    Data taken from
    https://etherscan.io/tx/0x7097e7e9ef2b8bb096ed98950875b4512a833d41ceb3246903e06b61665cd5cd
    """
    tx_hash = deserialize_evm_tx_hash('0x7097e7e9ef2b8bb096ed98950875b4512a833d41ceb3246903e06b61665cd5cd')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1687870007000)
    user_address = '0xcA74F404E0C7bfA35B13B511097df966D5a65597'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.001057637854578432'),
            location_label=user_address,
            notes='Burn 0.001057637854578432 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_WETH,
            amount=FVal('35'),
            location_label=user_address,
            notes=f'Swap 35 WETH in {CPT_ONEINCH_V4}',
            address=ONEINCH_V4_ROUTER,
            counterparty=CPT_ONEINCH_V4,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal('35'),
            location_label=user_address,
            notes=f'Receive 35 ETH as a result of a {CPT_ONEINCH_V4} swap',
            address=ONEINCH_V4_ROUTER,
            counterparty=CPT_ONEINCH_V4,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xdCB02829F91533Ab757b1B0e8B595D7c950AfBb8']])
def test_1inchv4_eth_weth_swap(ethereum_inquirer):
    """
    Test an 1inch v4 ETH to WETH swap via the WETH contract.

    Data taken from
    https://etherscan.io/tx/0x6446f928148dc9f7e1ad719730d661d6d3409a9c62293ca8e8c259d06c6bd004
    """
    tx_hash = deserialize_evm_tx_hash('0x6446f928148dc9f7e1ad719730d661d6d3409a9c62293ca8e8c259d06c6bd004')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1688039855000)
    user_address = '0xdCB02829F91533Ab757b1B0e8B595D7c950AfBb8'
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.002694727747581802'),
            location_label=user_address,
            notes='Burn 0.002694727747581802 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_ETH,
            amount=FVal('0.014763948338176106'),
            location_label=user_address,
            notes=f'Swap 0.014763948338176106 ETH in {CPT_ONEINCH_V4}',
            address=ONEINCH_V4_ROUTER,
            counterparty=CPT_ONEINCH_V4,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_WETH,
            amount=FVal('0.014763948338176106'),
            location_label=user_address,
            notes=f'Receive 0.014763948338176106 WETH as a result of a {CPT_ONEINCH_V4} swap',
            address=ONEINCH_V4_ROUTER,
            counterparty=CPT_ONEINCH_V4,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('polygon_pos_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_1inch_swap_polygon(polygon_pos_inquirer, polygon_pos_accounts):
    """Data taken from
    https://polygonscan.com/tx/0xe13e0ebab7a6abc0c0a22fcf0766b9a585a430415c88f3f90328b310119a85af
    """
    tx_hash = deserialize_evm_tx_hash('0xe13e0ebab7a6abc0c0a22fcf0766b9a585a430415c88f3f90328b310119a85af')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    user_addy = polygon_pos_accounts[0]
    pos_usdt = Asset('eip155:137/erc20:0xc2132D05D31c914a87C6611C10748AEb04B58e8F')
    pos_yfi = Asset('eip155:137/erc20:0xDA537104D6A5edd53c6fBba9A898708E465260b6')
    timestamp = TimestampMS(1641040985000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POLYGON_POS_MATIC,
            amount=FVal('0.0579902'),
            location_label=user_addy,
            notes='Burn 0.0579902 POL for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=277,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=pos_usdt,
            amount=FVal('115792089237316195423570985008687907853269984665640564039457584007913032.844935'),
            location_label=user_addy,
            address=ONEINCH_V4_ROUTER,
            notes=f'Set USDT spending approval of {user_addy} by {ONEINCH_V4_ROUTER} to 115792089237316195423570985008687907853269984665640564039457584007913032.844935',  # noqa: E501
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=278,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_subtype=HistoryEventSubType.SPEND,
            asset=pos_usdt,
            amount=FVal('96.795'),
            location_label=user_addy,
            notes='Swap 96.795 USDT in 1inch-v4',
            counterparty=CPT_ONEINCH_V4,
            address=ONEINCH_V4_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=279,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=pos_yfi,
            amount=FVal('0.002830144606136162'),
            location_label=user_addy,
            notes='Receive 0.002830144606136162 YFI as a result of a 1inch-v4 swap',
            counterparty=CPT_ONEINCH_V4,
            address=ONEINCH_V4_ROUTER,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('gnosis_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_1inch_gnosis_v5_swap(gnosis_inquirer, gnosis_accounts):
    tx_hash = deserialize_evm_tx_hash('0x4b1fcb8836d7cc323015c0d019f595273d176bd6024f7b59b4b15d3f7071ef71')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=gnosis_inquirer,
        tx_hash=tx_hash,
    )
    user_addy = gnosis_accounts[0]
    timestamp = TimestampMS(1693293950000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_XDAI,
            amount=FVal('0.0004273965'),
            location_label=user_addy,
            notes='Burn 0.0004273965 XDAI for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:100/erc20:0x9C58BAcC331c9aa871AFD802DB6379a98e80CEdb'),
            amount=FVal('0.044662144481150632'),
            location_label=user_addy,
            notes='Swap 0.044662144481150632 GNO in 1inch-v5',
            address=ONEINCH_V5_ROUTER,
            counterparty=CPT_ONEINCH_V5,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.GNOSIS,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:100/erc20:0x4ECaBa5870353805a9F068101A40E0f32ed605C6'),
            amount=FVal('4.522211'),
            location_label=user_addy,
            notes='Receive 4.522211 USDT as a result of a 1inch-v5 swap',
            counterparty=CPT_ONEINCH_V5,
            address=ONEINCH_V5_ROUTER,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('optimism_accounts', [['0x3Ba6eB0e4327B96aDe6D4f3b578724208a590CEF']])
def test_1inch_velodrome(optimism_inquirer, optimism_accounts):
    tx_hash = deserialize_evm_tx_hash('0x3cb68ee7dae76c0ca6466e3a593b32144d25eabb27c1ba416c83f154627d84d8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=optimism_inquirer,
        tx_hash=tx_hash,
    )
    user_addy = optimism_accounts[0]
    timestamp = TimestampMS(1698055881000)
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.000274323853192674'),
            location_label=user_addy,
            notes='Burn 0.000274323853192674 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:10/erc20:0x9560e827aF36c94D2Ac33a39bCE1Fe78631088Db'),
            amount=FVal('81.206684164250046887'),
            location_label=user_addy,
            notes='Swap 81.206684164250046887 VELO in 1inch-v5',
            address=ONEINCH_V5_ROUTER,
            counterparty=CPT_ONEINCH_V5,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.OPTIMISM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:10/erc20:0x1F32b1c2345538c0c6f582fCB022739c4A194Ebb'),
            amount=FVal('0.001577438860408636'),
            location_label=user_addy,
            notes='Receive 0.001577438860408636 wstETH as a result of a 1inch-v5 swap',
            counterparty=CPT_ONEINCH_V5,
            address=ONEINCH_V5_ROUTER,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr
@pytest.mark.parametrize('ethereum_accounts', [['0xC5d494aa0CBabD7871af0Ef122fB410Fa25c3379']])
def test_half_decoded_1inch_v5_swap(ethereum_inquirer, ethereum_accounts):
    """
    Test that if a swap using 1inch v5 has been  half decoded by other decoder (uniswap) first
    then the two legs of the swap are properly handled by the 1inch decoder.
    """
    tx_hash = deserialize_evm_tx_hash('0x0a86fef1df2e7f186cf7239083f67c424c735f91461388c5b23e01c4d6a4e7d8')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=ethereum_inquirer,
        tx_hash=tx_hash,
    )
    timestamp = TimestampMS(1701001727000)
    user_address = ethereum_accounts[0]
    expetec_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal('0.00205570157007332'),
            location_label=user_address,
            notes='Burn 0.00205570157007332 ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=1,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=A_LUSD,
            amount=FVal('115792089237316195423570985008687907853269984665640564038929.427407919914021705'),
            location_label=user_address,
            notes='Set LUSD spending approval of 0xC5d494aa0CBabD7871af0Ef122fB410Fa25c3379 by 0x1111111254EEB25477B68fb85Ed929f73A960582 to 115792089237316195423570985008687907853269984665640564038929.427407919914021705',  # noqa: E501
            address=ONEINCH_V5_ROUTER,
            counterparty=None,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.SPEND,
            asset=A_LUSD,
            amount=FVal('528.15659999321561823'),
            location_label=user_address,
            notes='Swap 528.15659999321561823 LUSD in 1inch-v5',
            address=ONEINCH_V5_ROUTER,
            counterparty=CPT_ONEINCH_V5,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.ETHEREUM,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_DAI,
            amount=FVal('521.366008657400952258'),
            location_label=user_address,
            notes='Receive 521.366008657400952258 DAI as a result of a 1inch-v5 swap',
            counterparty=CPT_ONEINCH_V5,
            address=ONEINCH_V5_ROUTER,
        ),
    ]
    assert events == expetec_events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('base_accounts', [['0xc37b40ABdB939635068d3c5f13E7faF686F03B65']])
def test_1inch_base_v6_swap(base_inquirer, base_accounts):
    tx_hash = deserialize_evm_tx_hash('0x5b41c094c49462cd97fc19dc898ef23c24f859b46dbd38ecf5d34d3d0fd291f5')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=base_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, gas, swap_amount, receive_amount = TimestampMS(1716833467000), '0.000019908608867869', '311804', '0.002362174980374604'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_ETH,
            amount=FVal(gas),
            location_label=base_accounts[0],
            notes=f'Burn {gas} ETH for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=2,
            timestamp=timestamp,
            location=Location.BASE,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:8453/erc20:0xAd1C24dE53fAD18270D5C99026302E989D212b41'),
            amount=ZERO,
            location_label=base_accounts[0],
            notes=f'Revoke BERD spending approval of {base_accounts[0]} by {ONEINCH_V6_ROUTER}',
            address=ONEINCH_V6_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=3,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:8453/erc20:0xAd1C24dE53fAD18270D5C99026302E989D212b41'),
            amount=FVal(swap_amount),
            location_label=base_accounts[0],
            notes=f'Swap {swap_amount} BERD in 1inch-v6',
            counterparty=CPT_ONEINCH_V6,
            address=ONEINCH_V6_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=4,
            timestamp=timestamp,
            location=Location.BASE,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=A_ETH,
            amount=FVal(receive_amount),
            location_label=base_accounts[0],
            notes=f'Receive {receive_amount} ETH as a result of a 1inch-v6 swap',
            counterparty=CPT_ONEINCH_V6,
            address=ONEINCH_V6_ROUTER,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('polygon_pos_accounts', [['0x9531C059098e3d194fF87FebB587aB07B30B1306']])
def test_1inchv4_swap_on_polygon(polygon_pos_inquirer, polygon_pos_accounts):
    tx_hash = deserialize_evm_tx_hash('0x4c1fcbc20fdd397229d9e3e88411fea589e7ceb901e770f6af2e70e89008d5fa')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(
        evm_inquirer=polygon_pos_inquirer,
        tx_hash=tx_hash,
    )
    timestamp, user, gas, amount_in, amount_out = TimestampMS(1653476213000), polygon_pos_accounts[0], '0.015694020167926014', '174.218999', '174.206'  # noqa: E501
    expected_events = [
        EvmEvent(
            tx_hash=tx_hash,
            sequence_index=0,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.SPEND,
            event_subtype=HistoryEventSubType.FEE,
            asset=A_POLYGON_POS_MATIC,
            amount=FVal(gas),
            location_label=user,
            notes=f'Burn {gas} POL for gas',
            counterparty=CPT_GAS,
        ), EvmEvent(
            tx_hash=tx_hash,
            sequence_index=20,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_type=HistoryEventType.INFORMATIONAL,
            event_subtype=HistoryEventSubType.APPROVE,
            asset=Asset('eip155:137/erc20:0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063'),  # DAI
            amount=FVal('115792089237316195423570985008687907853269984665640564039283.378007913129639935'),
            location_label=user,
            notes=f'Set DAI spending approval of {user} by {ONEINCH_V4_ROUTER} to 115792089237316195423570985008687907853269984665640564039283.378007913129639935',  # noqa: E501
            address=ONEINCH_V4_ROUTER,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=21,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_subtype=HistoryEventSubType.SPEND,
            asset=Asset('eip155:137/erc20:0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063'),  # DAI
            amount=FVal(amount_out),
            location_label=user,
            notes=f'Swap {amount_out} DAI in {CPT_ONEINCH_V4}',
            address=ONEINCH_V4_ROUTER,
            counterparty=CPT_ONEINCH_V4,
        ), EvmSwapEvent(
            tx_hash=tx_hash,
            sequence_index=22,
            timestamp=timestamp,
            location=Location.POLYGON_POS,
            event_subtype=HistoryEventSubType.RECEIVE,
            asset=Asset('eip155:137/erc20:0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174'),  # USDC
            amount=FVal(amount_in),
            location_label=user,
            notes=f'Receive {amount_in} USDC as a result of a {CPT_ONEINCH_V4} swap',
            address=ONEINCH_V4_ROUTER,
            counterparty=CPT_ONEINCH_V4,
        ),
    ]
    assert expected_events == events


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x4df4Ab179e3FdaC1930cd0a610D6bA6D5808E8Ff']])
def test_1inch4_swap_via_defi_plaza(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xa99ce12e628620861215c88ee2c51f6c0468442dfe0504c9e5f2c918cf63fc8c')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    timestamp, user, gas, amount_in, amount_out = TimestampMS(1657035153000), ethereum_accounts[0], '0.01345755735660528', '790.785045156438592337', '710.921537'  # noqa: E501
    assert events == [EvmEvent(
        tx_hash=tx_hash,
        sequence_index=0,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas),
        location_label=user,
        notes=f'Burn {gas} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal(amount_out),
        location_label=user,
        notes=f'Swap {amount_out} USDT in {CPT_ONEINCH_V4}',
        address=ONEINCH_V4_ROUTER,
        counterparty=CPT_ONEINCH_V4,
    ), EvmSwapEvent(
        tx_hash=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_CRV,
        amount=FVal(amount_in),
        location_label=user,
        notes=f'Receive {amount_in} CRV as a result of a {CPT_ONEINCH_V4} swap',
        address=ONEINCH_V4_ROUTER,
        counterparty=CPT_ONEINCH_V4,
    )]
