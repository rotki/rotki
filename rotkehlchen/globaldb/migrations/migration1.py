import json
from typing import TYPE_CHECKING

from rotkehlchen.constants.timing import ETH_PROTOCOLS_CACHE_REFRESH
from rotkehlchen.globaldb.cache import globaldb_set_unique_cache_value_at_ts
from rotkehlchen.types import CacheType, Timestamp
from rotkehlchen.utils.misc import ts_now

if TYPE_CHECKING:
    from rotkehlchen.db.drivers.sqlite import DBConnection

ilk_mapping = {  # ilk to (ilk_class, underlying_asset, join address)
    'BAT-A': (1, 'eip155:1/erc20:0x0D8775F648430679A709E98d2b0Cb6250d2887EF', '0x3D0B1912B66114d4096F48A8CEe3A56C231772cA'),  # noqa: E501
    'ETH-A': (1, 'ETH', '0x2F0b23f53734252Bda2277357e97e1517d6B042A'),
    'ETH-B': (1, 'ETH', '0x08638eF1A205bE6762A8b935F5da9b700Cf7322c'),
    'ETH-C': (1, 'ETH', '0xF04a5cC80B1E94C69B48f5ee68a08CD2F09A7c3E'),
    'KNC-A': (1, 'eip155:1/erc20:0xdd974D5C2e2928deA5F71b9825b8b646686BD200', '0x475F1a89C1ED844A08E8f6C50A00228b5E59E4A9'),  # noqa: E501
    'TUSD-A': (1, 'eip155:1/erc20:0x0000000000085d4780B73119b644AE5ecd22b376', '0x4454aF7C8bb9463203b66C816220D41ED7837f44'),  # noqa: E501
    'USDC-A': (1, 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', '0xA191e578a6736167326d05c119CE0c90849E84B7'),  # noqa: E501
    'USDC-B': (1, 'eip155:1/erc20:0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', '0x2600004fd1585f7270756DDc88aD9cfA10dD0428'),  # noqa: E501
    'USDT-A': (1, 'eip155:1/erc20:0xdAC17F958D2ee523a2206206994597C13D831ec7', '0x0Ac6A1D74E84C2dF9063bDDc31699FF2a2BB22A2'),  # noqa: E501
    'WBTC-A': (1, 'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', '0xBF72Da2Bd84c5170618Fbe5914B0ECA9638d5eb5'),  # noqa: E501
    'WBTC-B': (1, 'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', '0xfA8c996e158B80D77FbD0082BB437556A65B96E0'),  # noqa: E501
    'WBTC-C': (1, 'eip155:1/erc20:0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', '0x7f62f9592b823331E012D3c5DdF2A7714CfB9de2'),  # noqa: E501
    'ZRX-A': (1, 'eip155:1/erc20:0xE41d2489571d322189246DaFA5ebDe1F4699F498', '0xc7e8Cd72BDEe38865b4F5615956eF47ce1a7e5D0'),  # noqa: E501
    'MANA-A': (1, 'eip155:1/erc20:0x0F5D2fB29fb7d3CFeE444a200298f468908cC942', '0xA6EA3b9C04b8a38Ff5e224E7c3D6937ca44C0ef9'),  # noqa: E501
    'PAXUSD-A': (1, 'eip155:1/erc20:0x8E870D67F660D95d5be530380D0eC0bd388289E1', '0x7e62B7E279DFC78DEB656E34D6a435cC08a44666'),  # noqa: E501
    'COMP-A': (1, 'eip155:1/erc20:0xc00e94Cb662C3520282E6f5717214004A7f26888', '0xBEa7cDfB4b49EC154Ae1c0D731E4DC773A3265aA'),  # noqa: E501
    'LRC-A': (1, 'eip155:1/erc20:0xBBbbCA6A901c926F240b89EacB641d8Aec7AEafD', '0x6C186404A7A238D3d6027C0299D1822c1cf5d8f1'),  # noqa: E501
    'LINK-A': (1, 'eip155:1/erc20:0x514910771AF9Ca656af840dff83E8264EcF986CA', '0xdFccAf8fDbD2F4805C174f856a317765B49E4a50'),  # noqa: E501
    'BAL-A': (1, 'eip155:1/erc20:0xba100000625a3754423978a60c9317c58a424e3D', '0x4a03Aa7fb3973d8f0221B466EefB53D0aC195f55'),  # noqa: E501
    'YFI-A': (1, 'eip155:1/erc20:0x0bc529c00C6401aEF6D220BE8C6Ea1667F6Ad93e', '0x3ff33d9162aD47660083D7DC4bC02Fb231c81677'),  # noqa: E501
    'GUSD-A': (1, 'eip155:1/erc20:0x056Fd409E1d7A124BD7017459dFEa2F387b6d5Cd', '0xe29A14bcDeA40d83675aa43B72dF07f649738C8b'),  # noqa: E501
    'UNI-A': (1, 'eip155:1/erc20:0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', '0x3BC3A58b4FC1CbE7e98bB4aB7c99535e8bA9b8F1'),  # noqa: E501
    'RENBTC-A': (1, 'eip155:1/erc20:0xEB4C2781e4ebA804CE9a9803C67d0893436bB27D', '0xFD5608515A47C37afbA68960c1916b79af9491D0'),  # noqa: E501
    'AAVE-A': (1, 'eip155:1/erc20:0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', '0x24e459F61cEAa7b1cE70Dbaea938940A7c5aD46e'),  # noqa: E501
    'MATIC-A': (1, 'eip155:1/erc20:0x7D1AfA7B718fb893dB30A3aBc0Cfc608AaCfeBB0', '0x885f16e177d45fC9e7C87e1DA9fd47A9cfcE8E13'),  # noqa: E501
}


def globaldb_data_migration_1(conn: 'DBConnection') -> None:
    """Introduced at 1.27.1
    - Removes old setting last_assets_json_version (if existing)
    - Adds a makerdao vault types cache
    """
    with conn.write_ctx() as write_cursor:
        # Remove old setting if existing
        write_cursor.execute("DELETE FROM settings WHERE name='last_assets_json_version';")

        # Add a makerdao vault types cache, at a time that will allow refresh
        timestamp = Timestamp(ts_now() - ETH_PROTOCOLS_CACHE_REFRESH - 1)
        for ilk, info in ilk_mapping.items():
            globaldb_set_unique_cache_value_at_ts(
                write_cursor=write_cursor,
                key_parts=(CacheType.MAKERDAO_VAULT_ILK, ilk),
                value=json.dumps(info, separators=(',', ':')),
                timestamp=timestamp,
            )
