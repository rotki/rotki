import pytest

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.decoding.constants import CPT_GAS
from rotkehlchen.chain.ethereum.modules.zerion.constants import CPT_ZERION, ZERION_ROUTER
from rotkehlchen.constants.assets import A_ETH, A_USDC, A_USDT, A_WBTC
from rotkehlchen.fval import FVal
from rotkehlchen.history.events.structures.evm_event import EvmEvent
from rotkehlchen.history.events.structures.evm_swap import EvmSwapEvent
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.tests.utils.ethereum import get_decoded_events_of_transaction
from rotkehlchen.types import Location, TimestampMS, deserialize_evm_tx_hash


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x4030354D2d115cadfC53E835Ee20F9A3c0C339F3']])
def test_zerion_token_to_token(ethereum_inquirer, ethereum_accounts):
    tx_hash = deserialize_evm_tx_hash('0xd310b4079756aae680e37e17738b921aa178d332ec17caeb25b058c31eebbcc0')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1752853535000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.002307329927255016'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDT,
        amount=FVal(spend_amount := '3561.1'),
        location_label=user_address,
        notes=f'Swap {spend_amount} USDT in Zerion using Curve',
        counterparty=CPT_ZERION,
        address=ZERION_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_USDC,
        amount=FVal(receive_amount := '3562.9026'),
        location_label=user_address,
        notes=f'Receive {receive_amount} USDC as the result of a swap in Zerion',
        counterparty=CPT_ZERION,
        address=ZERION_ROUTER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x9217E71fA8aDD709Be42f31bD57Dc1D972405c55']])
def test_zerion_chained_adapters(ethereum_inquirer, ethereum_accounts):
    """Test a USDC deposit that goes through the Curve 3pool and then into the yearn vault"""
    tx_hash = deserialize_evm_tx_hash('0xd6bf15757d9100c05b02b2b1edfd3a8c7e94682da06f8b592bdc054ac397a37d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1609024552000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.019651626'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_USDC,
        amount=FVal(spend_amount := '200'),
        location_label=user_address,
        notes=f'Swap {spend_amount} USDC in Zerion using Curve, yearn.finance',
        counterparty=CPT_ZERION,
        address=ZERION_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0x9cA85572E6A3EbF24dEDd195623F188735A5179f'),
        amount=FVal(receive_amount := '192.736717437308987134'),
        location_label=user_address,
        notes=f'Receive {receive_amount} y3Crv as the result of a swap in Zerion',
        counterparty=CPT_ZERION,
        address=ZERION_ROUTER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0xEF08c3d5b02cF6240Cf71908D5dBD497e361584f']])
def test_zerion_eth_to_multiple_tokens(ethereum_inquirer, ethereum_accounts):
    """Test sending ETH to get uniswap LP tokens. The leftover WBTC is also returned"""
    tx_hash = deserialize_evm_tx_hash('0x155b1c43ddcbcfd32344fccf75ad743a4995a7266105c65c1df031358a35ed3d')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1608599293000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.050256672'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.SPEND,
        asset=A_ETH,
        amount=FVal(spend_amount := '0.67'),
        location_label=user_address,
        notes=f'Swap {spend_amount} ETH in Zerion using Weth, Uniswap V2',
        counterparty=CPT_ZERION,
        address=ZERION_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=Asset('eip155:1/erc20:0xcD7989894bc033581532D2cd88Da5db0A4b12859'),
        amount=FVal(lp_amount := '0.000005020882771596'),
        location_label=user_address,
        notes=f'Receive {lp_amount} UNI-V2 WBTC-BADGER as the result of a swap in Zerion',
        counterparty=CPT_ZERION,
        address=ZERION_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=3,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_type=HistoryEventType.MULTI_TRADE,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_WBTC,
        amount=FVal(wbtc_amount := '0.00003194'),
        location_label=user_address,
        notes=f'Receive {wbtc_amount} WBTC as the result of a swap in Zerion',
        counterparty=CPT_ZERION,
        address=ZERION_ROUTER,
    )]


@pytest.mark.vcr(filter_query_parameters=['apikey'])
@pytest.mark.parametrize('ethereum_accounts', [['0x98830840Da73b24865Ba67aF877956791D4178B0']])
def test_zerion_token_to_eth(ethereum_inquirer, ethereum_accounts):
    """Test a balancer pool exit whose WETH is unwrapped and sent back to the user as ETH"""
    tx_hash = deserialize_evm_tx_hash('0x94eaeb286e5e3e645e42643ae3e393fad45b9b1981809704b90a193543fc6f81')  # noqa: E501
    events, _ = get_decoded_events_of_transaction(evm_inquirer=ethereum_inquirer, tx_hash=tx_hash)
    assert events == [EvmEvent(
        tx_ref=tx_hash,
        sequence_index=0,
        timestamp=(timestamp := TimestampMS(1608597744000)),
        location=Location.ETHEREUM,
        event_type=HistoryEventType.SPEND,
        event_subtype=HistoryEventSubType.FEE,
        asset=A_ETH,
        amount=FVal(gas_amount := '0.01379231'),
        location_label=(user_address := ethereum_accounts[0]),
        notes=f'Burn {gas_amount} ETH for gas',
        counterparty=CPT_GAS,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=1,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.SPEND,
        asset=Asset('eip155:1/erc20:0x1efF8aF5D577060BA4ac8A29A13525bb0Ee2A3D5'),
        amount=FVal(spend_amount := '0.019'),
        location_label=user_address,
        notes=f'Swap {spend_amount} BPT in Zerion using Balancer, Weth',
        counterparty=CPT_ZERION,
        address=ZERION_ROUTER,
    ), EvmSwapEvent(
        tx_ref=tx_hash,
        sequence_index=2,
        timestamp=timestamp,
        location=Location.ETHEREUM,
        event_subtype=HistoryEventSubType.RECEIVE,
        asset=A_ETH,
        amount=FVal(receive_amount := '1.718541291343575251'),
        location_label=user_address,
        notes=f'Receive {receive_amount} ETH as the result of a swap in Zerion',
        counterparty=CPT_ZERION,
        address=ZERION_ROUTER,
    )]
