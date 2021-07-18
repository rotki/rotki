from rotkehlchen.chain.ethereum.modules.balancer import Balancer
from rotkehlchen.chain.ethereum.modules.balancer.utils import get_trades_from_tx_swaps
from rotkehlchen.chain.ethereum.trades import AMMSwap, AMMTrade
from rotkehlchen.chain.ethereum.typing import string_to_ethereum_address
from rotkehlchen.constants.assets import A_REN, A_SNX, A_USDC, A_WETH
from rotkehlchen.constants.misc import ZERO
from rotkehlchen.fval import FVal
from rotkehlchen.tests.api.test_balancer import get_balancer_test_addr2_expected_trades
from rotkehlchen.tests.utils.constants import A_AMPL
from rotkehlchen.typing import AssetAmount, Location, Price, Timestamp, TradeType

TEST_SWAPS_TX_1 = [
    AMMSwap(
        tx_hash='0x1b0d3525964d8e5fbcc0dcdeebcced4bec9017f648e97c3c9761fda1ca6e7b22',
        log_index=254,
        address=string_to_ethereum_address('0x8e670b4d6651C4051e65B21AA4a575F3f99b8B83'),
        from_address=string_to_ethereum_address('0x65003947dC16956AfC4400008606001500940000'),
        to_address=string_to_ethereum_address('0x7860E28ebFB8Ae052Bfe279c07aC5d94c9cD2937'),
        timestamp=Timestamp(1614094145),
        location=Location.BALANCER,
        token0=A_USDC,
        token1=A_AMPL,
        amount0_in=AssetAmount(FVal('12401.224639')),
        amount1_in=AssetAmount(ZERO),
        amount0_out=AssetAmount(ZERO),
        amount1_out=AssetAmount(FVal('14285.153512382')),
    ),
]
TEST_SWAPS_TX_2 = [
    AMMSwap(
        tx_hash='0x1b0d3525964d8e5fbcc0dcdeebcced4bec9017f648e97c3c9761fda1ca6e7b22',
        log_index=254,
        address=string_to_ethereum_address('0x8e670b4d6651C4051e65B21AA4a575F3f99b8B83'),
        from_address=string_to_ethereum_address('0x65003947dC16956AfC4400008606001500940000'),
        to_address=string_to_ethereum_address('0x7860E28ebFB8Ae052Bfe279c07aC5d94c9cD2937'),
        timestamp=Timestamp(1614094145),
        location=Location.BALANCER,
        token0=A_USDC,
        token1=A_AMPL,
        amount0_in=AssetAmount(FVal('12401.224639')),
        amount1_in=AssetAmount(ZERO),
        amount0_out=AssetAmount(ZERO),
        amount1_out=AssetAmount(FVal('14285.153512382')),
    ),
    AMMSwap(
        tx_hash='0x1b0d3525964d8e5fbcc0dcdeebcced4bec9017f648e97c3c9761fda1ca6e7b22',
        log_index=258,
        address=string_to_ethereum_address('0x8e670b4d6651C4051e65B21AA4a575F3f99b8B83'),
        from_address=string_to_ethereum_address('0x65003947dC16956AfC4400008606001500940000'),
        to_address=string_to_ethereum_address('0xa751A143f8fe0a108800Bfb915585E4255C2FE80'),
        timestamp=Timestamp(1614094145),
        location=Location.BALANCER,
        token0=A_AMPL,
        token1=A_WETH,
        amount0_in=AssetAmount(FVal('14285.153512382')),
        amount1_in=AssetAmount(ZERO),
        amount0_out=AssetAmount(ZERO),
        amount1_out=AssetAmount(FVal('8.05955457343053505')),
    ),
]
TEST_SWAPS_TX_3 = [
    AMMSwap(
        tx_hash='0x70b50d011f23f8437aa32b4155972098b34b5fb19b02198f3bc7f2456c4c3ffc',
        log_index=2,
        address=string_to_ethereum_address('0x029f388ac4d5c8bff490550ce0853221030e822b'),
        from_address=string_to_ethereum_address('0x0000000000007f150bd6f54c40a34d7c3d5e9f56'),
        to_address=string_to_ethereum_address('0x5a21e141ca90e46a2ee54f93b54a1bec608c307b'),
        timestamp=Timestamp(1614150923),
        location=Location.BALANCER,
        token0=A_WETH,
        token1=A_REN,
        amount0_in=AssetAmount(FVal('2.19139968')),
        amount1_in=AssetAmount(ZERO),
        amount0_out=AssetAmount(ZERO),
        amount1_out=AssetAmount(FVal('3197.944466059874991601')),
    ),
    AMMSwap(
        tx_hash='0x70b50d011f23f8437aa32b4155972098b34b5fb19b02198f3bc7f2456c4c3ffc',
        log_index=6,
        address=string_to_ethereum_address('0x029f388ac4d5c8bff490550ce0853221030e822b'),
        from_address=string_to_ethereum_address('0x0000000000007f150bd6f54c40a34d7c3d5e9f56'),
        to_address=string_to_ethereum_address('0x80cba5ba9259c08851d94d6bf45e248541fb3e86'),
        timestamp=Timestamp(1614150923),
        location=Location.BALANCER,
        token0=A_REN,
        token1=A_SNX,
        amount0_in=AssetAmount(FVal('3197.944466059790123008')),
        amount1_in=AssetAmount(ZERO),
        amount0_out=AssetAmount(ZERO),
        amount1_out=AssetAmount(FVal('186.643670114899291543')),
    ),
    AMMSwap(
        tx_hash='0x70b50d011f23f8437aa32b4155972098b34b5fb19b02198f3bc7f2456c4c3ffc',
        log_index=10,
        address=string_to_ethereum_address('0x029f388ac4d5c8bff490550ce0853221030e822b'),
        from_address=string_to_ethereum_address('0x0000000000007f150bd6f54c40a34d7c3d5e9f56'),
        to_address=string_to_ethereum_address('0xe3f9cf7d44488715361581dd8b3a15379953eb4c'),
        timestamp=Timestamp(1614150923),
        location=Location.BALANCER,
        token0=A_SNX,
        token1=A_WETH,
        amount0_in=AssetAmount(FVal('186.643670114899034112')),
        amount1_in=AssetAmount(ZERO),
        amount0_out=AssetAmount(ZERO),
        amount1_out=AssetAmount(FVal('2.283067259355947642')),
    ),
]


def test_get_trades_from_tx_swaps_1():
    """Single swap"""
    trades = get_trades_from_tx_swaps(TEST_SWAPS_TX_1)
    expected_trades = [
        AMMTrade(
            trade_type=TradeType.BUY,
            base_asset=A_AMPL,
            quote_asset=A_USDC,
            amount=AssetAmount(FVal('14285.153512382')),
            rate=Price(FVal('0.8681198020203941533693340847')),
            trade_index=0,
            swaps=TEST_SWAPS_TX_1,
        ),
    ]
    assert trades == expected_trades


def test_get_trades_from_tx_swaps_2():
    """Two swaps that can be aggregated"""
    trades = get_trades_from_tx_swaps(TEST_SWAPS_TX_2)
    expected_trades = [
        AMMTrade(
            trade_type=TradeType.BUY,
            base_asset=A_WETH,
            quote_asset=A_USDC,
            amount=AssetAmount(FVal('8.05955457343053505')),
            rate=Price(FVal('1538.698513176199118305140044')),
            trade_index=0,
            swaps=TEST_SWAPS_TX_2,
        ),
    ]
    assert trades == expected_trades


def test_get_trades_from_tx_swaps_3():
    """Three swaps that can't be aggregated"""
    trades = get_trades_from_tx_swaps(TEST_SWAPS_TX_3)
    expected_trades = [
        AMMTrade(
            trade_type=TradeType.BUY,
            base_asset=A_REN,
            quote_asset=A_WETH,
            amount=AssetAmount(FVal('3197.944466059874991601')),
            rate=Price(FVal('0.0006852525749766945789823189473')),
            trade_index=0,
            swaps=[TEST_SWAPS_TX_3[0]],
        ),
        AMMTrade(
            trade_type=TradeType.BUY,
            base_asset=A_SNX,
            quote_asset=A_REN,
            amount=AssetAmount(FVal('186.643670114899291543')),
            rate=Price(FVal('17.13395618555459553468367999')),
            trade_index=1,
            swaps=[TEST_SWAPS_TX_3[1]],
        ),
        AMMTrade(
            trade_type=TradeType.BUY,
            base_asset=A_WETH,
            quote_asset=A_SNX,
            amount=AssetAmount(FVal('2.283067259355947642')),
            rate=Price(FVal('81.75127970936394514208635428')),
            trade_index=2,
            swaps=[TEST_SWAPS_TX_3[2]],
        ),
    ]
    assert trades == expected_trades


def test_get_trades_from_swaps():
    addr2_expected_trades = get_balancer_test_addr2_expected_trades()
    swaps = [
        addr2_expected_trades[1].swaps[0],  # log_index 18
        addr2_expected_trades[0].swaps[0],  # log_index 24
        addr2_expected_trades[2].swaps[0],  # log_index 143
    ]
    expected_trades = addr2_expected_trades[0:3][::-1]
    trades = Balancer._get_trades_from_swaps(swaps)
    assert trades == expected_trades
