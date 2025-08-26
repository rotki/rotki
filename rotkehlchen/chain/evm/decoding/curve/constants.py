from typing import Final, Literal, get_args

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

CPT_CURVE: Final = 'curve'
CURVE_COUNTERPARTY_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_CURVE,
    label='Curve.fi',
    image='curve.png',
)
ADD_LIQUIDITY_2_ASSETS: Final = b'&\xf5Z\x85\x08\x1d$\x97N\x85\xc6\xc0\x00E\xd0\xf0E9\x91\xe9Xs\xf5+\xff\r!\xaf@y\xa7h'  # noqa: E501
ADD_LIQUIDITY_2_ASSETS_OPTIMIZED: Final = b'q\x96\xcb\xf6=\xf1\xf2\xec c\x8eh>\xbeQ\xd1\x82`\xbeQ\x05\x92\xee\x1e.\xfe?<\xfdL3\xe9'  # in CurveTwocryptoOptimized  # noqa: E501
ADD_LIQUIDITY_3_ASSETS: Final = b'B?d\x95\xa0\x8f\xc6RB\\\xf4\xed\r\x1f\x9e7\xe5q\xd9\xb9R\x9b\x1c\x1c#\xcc\xe7\x80\xb2\xe7\xdf\r'  # noqa: E501
ADD_LIQUIDITY_4_ASSETS: Final = b'?\x19\x15w^\x0c\x9a8\xa5z{\xb7\xf1\xf9\x00_Ho\xb9\x04\xe1\xf8J\xa2\x156MVs\x19\xa5\x8d'  # noqa: E501
ADD_LIQUIDITY_DYNAMIC_ASSETS: Final = b'\x18\x9cb;fk\x1bE\xb8=qx\xf3\x9b\x8c\x08|\xb0\x97t1|\xa2\xf5<-<7&\xf2"\xa2'  # in DepositAndStake Zap  # noqa: E501
ADD_LIQUIDITY_EVENTS: Final = {
    ADD_LIQUIDITY_2_ASSETS,
    ADD_LIQUIDITY_2_ASSETS_OPTIMIZED,
    ADD_LIQUIDITY_3_ASSETS,
    ADD_LIQUIDITY_4_ASSETS,
    ADD_LIQUIDITY_DYNAMIC_ASSETS,
}
ADD_LIQUIDITY_TOKEN_COUNTS: Final = {
    ADD_LIQUIDITY_2_ASSETS: 2,
    ADD_LIQUIDITY_2_ASSETS_OPTIMIZED: 2,
    ADD_LIQUIDITY_3_ASSETS: 3,
    ADD_LIQUIDITY_4_ASSETS: 4,
}
ADD_LIQUIDITY_IN_DEPOSIT_AND_STAKE = b'T\n\xb3\x85\xf9\xb5\xd4P\xa2t\x04\x17,\xaa\xdeQk;\xa3\xf4\xbe\x88#\x9a\xc5j*\xd1\xde*\x1fZ'  # noqa: E501
REMOVE_LIQUIDITY_IMBALANCE: Final = {
    b'\xb9d\xb7/s\xf5\xef[\xf0\xfd\xc5Y\xb2\xfa\xb9\xa7\xb1*9\xe4x\x17\xa5G\xf1\xf0\xae\xe4\x7f\xeb\xd6\x02',
    b'+U\x087\x8d~\x19\xe0\xd5\xfa3\x84\x19\x03G1AlO[!\x9a\x107\x99V\xf7d1\x7f\xd4~',
}
REMOVE_LIQUIDITY_3_ASSETS: Final = b'\xa4\x9dL\xf0&V\xae\xbf\x8cw\x1fZ\x85\x85c\x8a*\x15\xeel\x97\xcfr\x05\xd4 \x8e\xd7\xc1\xdf%-'  # noqa: E501
REMOVE_LIQUIDITY_4_ASSETS: Final = b'\x98x\xca7^\x10o*C\xc3\xb5\x99\xfcbEh\x13\x1cL\x9aK\xa6j\x14V7\x15v;\xe9\xd5\x9d'  # noqa: E501
REMOVE_LIQUIDITY_CLASSIC: Final = b"Z\xd0V\xf2\xe2\x8a\x8c\xec# \x15@k\x846h\xc1\xe3l\xdaY\x81'\xec;\x8cY\xb8\xc7's\xa0"  # noqa: E501
REMOVE_LIQUIDITY_EVENTS: Final = {
    *REMOVE_LIQUIDITY_IMBALANCE,
    REMOVE_LIQUIDITY_3_ASSETS,
    REMOVE_LIQUIDITY_4_ASSETS,
    REMOVE_LIQUIDITY_CLASSIC,
    b'|68T\xcc\xf7\x96#A\x1f\x89\x95\xb3b\xbc\xe5\xed\xdf\xf1\x8c\x92~\xdco]\xbb\xb5\xe0X\x19\xa8,',  # REMOVE_LIQUIDITY  # noqa: E501,
    b'\x9e\x96\xdd;\x99z*%~\xecM\xf9\xbbn\xafbn m\xf5\xf5C\xbd\x966\x82\xd1C0\x0b\xe3\x10',  # REMOVE_ONE  # noqa: E501
    b"Z\xd0V\xf2\xe2\x8a\x8c\xec# \x15@k\x846h\xc1\xe3l\xdaY\x81'\xec;\x8cY\xb8\xc7's\xa0",  # REMOVE_LIQUIDITY  # noqa: E501,
    b'\xdd<\x036\xa1o\x1bd\xf1r\xb7\xbb\r\xad[+<|v\xf9\x1e\x8cJ\xaf\xd6\xaa\xe6\r\xce\x80\x01S',  # RemoveLiquidity in CurveTwocryptoOptimized  # noqa: E501
    b"oH\x12\x9d\xb1\xf3|\xcb\x9c\xc5\xdd~\x11\x9c\xb3'P\xca\xbd\xf7[H7]s\r&\xce6Y\xbb\xe1",  # RemoveLiquidityOne  # noqa: E501
    b'\xe2\x00\xe2MJL|\xd3g\xdd\x9b\xef\xe3\x94\xdc\x8a\x14\xe6\xd5\x8c\x88\xff^/Q-e\xa9\xe0\xaa\x9c\\',  # RemoveLiquidityOne  # noqa: E501
}
REMOVE_LIQUIDITY_TOKEN_COUNTS: Final = {
    REMOVE_LIQUIDITY_CLASSIC: 2,
    REMOVE_LIQUIDITY_3_ASSETS: 3,
    REMOVE_LIQUIDITY_4_ASSETS: 4,
}
GAUGE_DEPOSIT: Final = b'\xe1\xff\xfc\xc4\x92=\x04\xb5Y\xf4\xd2\x9a\x8b\xfcl\xda\x04\xeb[\r<F\x07Q\xc2@,\\\\\xc9\x10\x9c'  # noqa: E501
GAUGE_WITHDRAW: Final = b'\x88N\xda\xd9\xceo\xa2D\r\x8aT\xcc\x124\x90\xeb\x96\xd2v\x84y\xd4\x9f\xf9\xc76a%\xa9BCd'  # noqa: E501
GAUGE_VOTE: Final = b'E\xca\x9aL\x8d\x01\x19\xeb2\x9eX\r(\xfeh\x9eHN\x1b\xe20\xda\x807\xad\xe9T}-%\xcc\x91'  # noqa: E501
TOKEN_EXCHANGE: Final = b'\x8b>\x96\xf2\xb8\x89\xfaw\x1cS\xc9\x81\xb4\r\xaf\x00_c\xf67\xf1\x86\x9fppR\xd1Z=\xd9q@'  # noqa: E501
TOKEN_EXCHANGE_UNDERLYING: Final = b'\xd0\x13\xca#\xe7ze\x00<,e\x9cTB\xc0\x0c\x80Sq\xb7\xfc\x1e\xbdL lA\xd1Sk\xd9\x0b'  # noqa: E501
# token exchange topic of new generation (NG) pools
TOKEN_EXCHANGE_NG: Final = b'\x14?\x1f\x8e\x86\x1f\xbd\xed\xdd[F\xe8D\xb7\xd3\xac{\x86\xa1"\xf3n\x8cF8Y\xeeh\x11\xb1\xf2\x9c'  # noqa: E501
EXCHANGE_MULTIPLE: Final = b'\x14\xb5a\x17\x8a\xe0\xf3h\xf4\x0f\xaf\xd0H\\Oq)\xeaq\xcd\xc0\x0bL\xe1\xe5\x94\x0f\x9b\xc6Y\xc8\xb2'  # noqa: E501
# token exchange topic of new generation (NG) router
EXCHANGE_NG: Final = b'V\xd0f\x1e$\r\xfb\x19\x9e\xf1\x96\xe1noBG9\x906c\x14\xf0"j\xc9x\xf7\xbe<\xd9\xee\x83'  # noqa: E501
MINTED_CRV: Final = b'\x9d"\x8di\xb5\xfd\xb8\xd2s\xa23o\x8f\xb8a-\x03\x961\x02N\xa9\xbf\t\xc4$\xa9P:\xa0x\xf0'  # noqa: E501

# list of pools that we know contain bad tokens
IGNORED_CURVE_POOLS = {'0x066B6e1E93FA7dcd3F0Eb7f8baC7D5A747CE0BF9'}
CURVE_BASE_API_URL = 'https://api.curve.finance'
CURVE_API_URL = f'{CURVE_BASE_API_URL}/' + 'v1/getPools/all/{curve_blockchain_id}'
CURVE_CHAIN_ID = {
    ChainID.ETHEREUM: 'ethereum',
    ChainID.POLYGON_POS: 'polygon',
    ChainID.OPTIMISM: 'optimism',
    ChainID.ARBITRUM_ONE: 'arbitrum',
    ChainID.GNOSIS: 'xdai',
    ChainID.BASE: 'base',
    ChainID.BINANCE_SC: 'bsc',
}
CURVE_CHAIN_ID_TYPE = Literal[
    ChainID.ETHEREUM,
    ChainID.POLYGON_POS,
    ChainID.OPTIMISM,
    ChainID.ARBITRUM_ONE,
    ChainID.GNOSIS,
    ChainID.BASE,
    ChainID.BINANCE_SC,
]
CURVE_CHAIN_IDS: tuple[CURVE_CHAIN_ID_TYPE, ...] = get_args(CURVE_CHAIN_ID_TYPE)
CURVE_METAREGISTRY_METHODS = [
    'get_pool_name',
    'get_gauge',
    'get_lp_token',
    'get_coins',
    'get_underlying_coins',
]
# The address provider address is same for all the supported chains
CURVE_ADDRESS_PROVIDER: Final = string_to_evm_address('0x5ffe7FB82894076ECB99A30D6A32e969e6e35E98')
CURVE_SWAP_ROUTER_NG: Final = string_to_evm_address('0xF0d4c12A5768D806021F80a262B4d39d26C58b8D')
DEPOSIT_AND_STAKE_ZAP: Final = string_to_evm_address('0x37c5ab57AF7100Bdc9B668d766e193CCbF6614FD')
CHILD_LIQUIDITY_GAUGE_FACTORY: Final = string_to_evm_address('0xabC000d88f23Bb45525E447528DBF656A9D55bf5')  # noqa: E501
# Maximum number of pools to query from the onchain metaregistry. Querying too many pools onchain
# takes a very long time.  When testing this ~500 pools took ~10 minutes. Setting the max to 50
# here so it should only spend about 1 minute on each chain.
MAX_ONCHAIN_POOLS_QUERY: Final = 50
