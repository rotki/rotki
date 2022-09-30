from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.assets.asset import EvmToken
from rotkehlchen.chain.ethereum.interfaces.ammswap.types import EventType, LiquidityPoolEvent
from rotkehlchen.chain.ethereum.modules.balancer.db import add_balancer_events
from rotkehlchen.chain.ethereum.modules.balancer.types import BalancerBPTEventType, BalancerEvent
from rotkehlchen.constants.assets import A_ETH, A_EUR, A_LTC, A_USD, A_USDC
from rotkehlchen.constants.misc import ONE, ZERO
from rotkehlchen.exchanges.data_structures import Trade
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    ApiKey,
    ApiSecret,
    AssetAmount,
    ChecksumEvmAddress,
    Fee,
    Location,
    Price,
    Timestamp,
    TradeType,
    deserialize_evm_tx_hash,
)


def test_associated_locations(database):
    """Test that locations imported in different places are correctly stored in database"""
    # Add trades from different locations
    trades = [Trade(
        timestamp=Timestamp(1595833195),
        location=Location.CRYPTOCOM,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('1.0')),
        rate=Price(FVal('281.14')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1587825824),
        location=Location.CRYPTOCOM,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('50.0')),
        rate=Price(FVal('3.521')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1596014214),
        location=Location.BLOCKFI,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('50.0')),
        rate=Price(FVal('3.521')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1565888464),
        location=Location.NEXO,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('50.0')),
        rate=Price(FVal('3.521')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1596014214),
        location=Location.NEXO,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('50.0')),
        rate=Price(FVal('3.521')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1612051199),
        location=Location.BLOCKFI,
        base_asset=A_USDC,
        quote_asset=A_LTC,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('6404.6')),
        rate=Price(FVal('151.6283999982779809352223797')),
        fee=None,
        fee_currency=None,
        link='',
        notes='One Time',
    ), Trade(
        timestamp=Timestamp(1595833195),
        location=Location.POLONIEX,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('1.0')),
        rate=Price(FVal('281.14')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1596429934),
        location=Location.COINBASE,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('0.00061475')),
        rate=Price(FVal('309.0687271248474989833265555')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='',
    ), Trade(
        timestamp=Timestamp(1596429934),
        location=Location.EXTERNAL,
        base_asset=A_ETH,
        quote_asset=A_EUR,
        trade_type=TradeType.BUY,
        amount=AssetAmount(FVal('1')),
        rate=Price(FVal('320')),
        fee=Fee(ZERO),
        fee_currency=A_USD,
        link='',
        notes='',
    )]

    # Add multiple entries for same exchange + connected exchange
    with database.user_write() as cursor:
        database.add_trades(cursor, trades)
        kraken_api_key1 = ApiKey('kraken_api_key')
        kraken_api_secret1 = ApiSecret(b'kraken_api_secret')
        kraken_api_key2 = ApiKey('kraken_api_key2')
        kraken_api_secret2 = ApiSecret(b'kraken_api_secret2')
        binance_api_key = ApiKey('binance_api_key')
        binance_api_secret = ApiSecret(b'binance_api_secret')

        # add mock kraken and binance
        database.add_exchange('kraken1', Location.KRAKEN, kraken_api_key1, kraken_api_secret1)
        database.add_exchange('kraken2', Location.KRAKEN, kraken_api_key2, kraken_api_secret2)
        database.add_exchange('binance', Location.BINANCE, binance_api_key, binance_api_secret)

        # Add uniswap and sushiswap events
        database.add_amm_events(cursor, [
            LiquidityPoolEvent(
                tx_hash=deserialize_evm_tx_hash(
                    '0x47ea26957ce09e84a51b51dfdab6a4ac1c3672a372eef77b15ef7677174ac847',
                ),
                log_index=23,
                address=ChecksumEvmAddress('0x3163Bb273E8D9960Ce003fD542bF26b4C529f515'),
                timestamp=Timestamp(1590011534),
                event_type=EventType.MINT_SUSHISWAP,
                pool_address=ChecksumEvmAddress('0xa2107FA5B38d9bbd2C461D6EDf11B11A50F6b974'),
                token0=EvmToken('eip155:1/erc20:0x514910771AF9Ca656af840dff83E8264EcF986CA'),
                token1=EvmToken('eip155:1/erc20:0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
                amount0=FVal('3.313676003468974932'),
                amount1=FVal('0.064189269269768657'),
                usd_price=FVal('26.94433946158740371839009166230438'),
                lp_amount=FVal('0.460858304063739927'),
            ),
        ])
        add_balancer_events(
            cursor,
            [
                BalancerEvent(
                    tx_hash='0xa54bf4c68d435e3c8f432fd7e62b7f8aca497a831a3d3fca305a954484ddd7b3',
                    log_index=23,
                    address=ChecksumEvmAddress('0xa2107FA5B38d9bbd2C461D6EDf11B11A50F6b974'),
                    timestamp=Timestamp(1609301469),
                    event_type=BalancerBPTEventType.MINT,
                    pool_address_token=EvmToken('eip155:1/erc20:0x514910771AF9Ca656af840dff83E8264EcF986CA'),  # noqa: E501
                    lp_balance=Balance(amount=FVal(2), usd_value=FVal(3)),
                    amounts=[
                        AssetAmount(ONE),
                        AssetAmount(FVal(2)),
                    ],
                ),
            ],
            msg_aggregator=database.msg_aggregator,
        )
    expected_locations = {
        Location.KRAKEN,
        Location.BINANCE,
        Location.BLOCKFI,
        Location.NEXO,
        Location.CRYPTOCOM,
        Location.POLONIEX,
        Location.COINBASE,
        Location.EXTERNAL,
        Location.SUSHISWAP,
        Location.BALANCER,
    }

    assert set(database.get_associated_locations()) == expected_locations
