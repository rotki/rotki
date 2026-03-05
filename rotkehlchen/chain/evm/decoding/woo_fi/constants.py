from typing import Final

from eth_typing import ABI

from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

CPT_WOO_FI: Final = 'woo-fi'
CPT_WOO_FI_LABEL: Final = 'WOOFi'

WOO_ROUTER_V2: Final = string_to_evm_address('0x4c4AF8DBc524681930a27b2F1Af5bcC8062E6fB7')
WOO_CROSS_SWAP_ROUTER_V5: Final = string_to_evm_address('0xB84aEfEF2DDDE628d5c7F1fba320dE63e3f4757c')  # noqa: E501
WOO_REWARD_MASTER_CHEF: Final = string_to_evm_address('0xc0f8C29e3a9A7650a3F642e467d70087819926d6')
WOO_ROUTER_SWAP_TOPIC: Final = b"'\xc9\x8e\x91\x1e\xfd\xd2$\xf4\x00/l\xd81\xc3\xad\r'Y\xee\x17o\x9e\xe8Fm\x95\x82j\xf2*\x1c"  # noqa: E501
WOO_CROSS_SWAP_ON_SRC_CHAIN_TOPIC: Final = b'\x8d\xbfa\xe7L\x14\xd5\xd85\x81jk\xda\xf0\x87K\xd5\xf7\xbf\xf3\xeeM\x8cL\x83\xd0\xe6\xbf\x8d\xa4\xcfr'  # noqa: E501
WOO_CROSS_SWAP_ON_DEST_CHAIN_TOPIC: Final = b'\x96\xdd\xa4\xec\xb8m8\xbc\x80nC\xde }m`"IG\xe1$J#\x08\x9bV\x8fhV\xeb\xa6\xb5'  # noqa: E501
WOO_REQUEST_WITHDRAW_TOPIC: Final = b'\xeb\xea\xa8xR\x85\xa4\xf7\xc3z0SQ\x99}\xce\xeb\xab\xc3\xc3W\xda\xb9\x80#\xdc7QJ\x1bn\xd6'  # noqa: E501
WOO_INSTANT_WITHDRAW_TOPIC: Final = b'g \x04\xd3Z\xd2\x12O\x90)\x93q\xad\xe9\\\xf5YE\x00\xe4\x07\x05\xa7\xcfn\xaf|\x00\xb5Z\x07\xac'  # noqa: E501
WOO_ON_REWARDED_TOPIC: Final = b"\x92L\xd6\n|'\x92\xf2:\xc2\t\x027\xad\xb3\x99`\x92\xfa\xc4\xbe6D\xcf\xdc'\x10d\xf5;W\x04"  # noqa: E501
WOO_RESERVE_WITHDRAW_TOPIC: Final = b'$\xbd#\xbf8\x1f\xbev\x9fd\xbc\r\x8b\xff\x86\xa8\t\xb6\xc3t\xaeU{\xe6!\xb9\xc7+\x88\x16\xf4\xa5'  # noqa: E501
WOO_INSTANT_UNSTAKE_TOPIC: Final = b'\xab-\xaf<\x14l\xa6Al\xbc\xcd*\x86\xed+\xa9\x95\xe1q\xefc\x19\xdf\x14\xa3\x8a\xef\x01@:\x9c\x96'  # noqa: E501
WOO_STAKE_ON_PROXY_TOPIC: Final = b'\xe8NJ\xc7C\x9e\x00\xdd\x9d"7=\xcd\xedU\xa0V\x05}|\xd1\x06\xd0\x97t\xe4\xa3j\xb3;q1'  # noqa: E501
WOO_UNSTAKE_ON_PROXY_TOPIC: Final = b'\xde`\xe2\xb8\x81\xeb\xad\xb1\xbbM<\x07\x0cf5Q\x0c\xde\xefY\x91?\xf1\xff\x86K\x01`\xe7\xe3\r\x97'  # noqa: E501
WOO_STAKE_ON_LOCAL_TOPIC: Final = b'\xb8\x01\x98\xf3\xdc\xe5\xb4LvU\xdc\x02\xc2\xd1\xe8\xaf$>\x94:u\xd3P\xba\xb8\xb5f\xc6+\xea\xdd\x11'  # noqa: E501
WOO_UNSTAKE_ON_LOCAL_TOPIC: Final = b'\xd4\xc6P\xa7?\x8d\x15\xda\xb8{N\x93\xc9\xca\xaaw\xb24\x19[\x0b\x87;\x80mu\xc1\x18a%\x04z'  # noqa: E501

WOO_REWARD_MASTER_CHEF_ABI: Final[ABI] = [{
    'inputs': [{'name': '', 'type': 'uint256'}],
    'name': 'poolInfo',
    'outputs': [
        {'name': 'weToken', 'type': 'address'},
        {'name': 'allocPoint', 'type': 'uint256'},
        {'name': 'lastRewardBlock', 'type': 'uint256'},
        {'name': 'accTokenPerShare', 'type': 'uint256'},
        {'name': 'rewarder', 'type': 'address'},
    ],
    'stateMutability': 'view',
    'type': 'function',
}, {
    'inputs': [{'name': '', 'type': 'uint256'}, {'name': '', 'type': 'address'}],
    'name': 'userInfo',
    'outputs': [{'name': 'amount', 'type': 'uint256'}, {'name': 'rewardDebt', 'type': 'uint256'}],
    'stateMutability': 'view',
    'type': 'function',
}]
WOO_STAKE_V1_OR_VAULT_ABI: Final[ABI] = [{
    'inputs': [],
    'name': 'getPricePerFullShare',
    'outputs': [{'name': '', 'type': 'uint256'}],
    'stateMutability': 'view',
    'type': 'function',
}]
WOO_STAKE_V2_ABI: Final[ABI] = [{
    'inputs': [{'name': '', 'type': 'address'}],
    'name': 'balances',
    'outputs': [{'name': '', 'type': 'uint256'}],
    'stateMutability': 'view',
    'type': 'function',
}]

# For WOOFi cross-chain swaps, the only way to tell what chain it is from/to is by the LayerZero
# endpoint id. These ids are not directly correlated to chain ids, so we need to map them here.
# https://docs.layerzero.network/v2/faq#whats-the-difference-between-endpoint-id-eid-and-chain-id
# Also see https://docs.layerzero.network/v2/deployments/deployed-contracts for mappings list
LAYER_ZERO_EID_TO_CHAIN_ID: Final = {
    30101: ChainID.ETHEREUM,
    30111: ChainID.OPTIMISM,
    30102: ChainID.BINANCE_SC,
    30145: ChainID.GNOSIS,
    30109: ChainID.POLYGON_POS,
    30112: ChainID.FANTOM,
    30184: ChainID.BASE,
    30110: ChainID.ARBITRUM_ONE,
    30106: ChainID.AVALANCHE,
    30125: ChainID.CELO,
    30175: ChainID.ARBITRUM_NOVA,
    30359: ChainID.CRONOS,
    30158: ChainID.POLYGON_ZKEVM,
    30165: ChainID.ZKSYNC_ERA,
    30214: ChainID.SCROLL,
    30332: ChainID.SONIC,
    30183: ChainID.LINEA,
}
