from typing import Final, NamedTuple

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID, ChecksumEvmAddress

CPT_PRIVACY_POOLS: Final = 'privacy-pools'
PRIVACY_POOLS_LABEL: Final = 'Privacy Pools'
PRIVACY_POOLS_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_PRIVACY_POOLS,
    label=PRIVACY_POOLS_LABEL,
    image='privacy_pools.svg',
)

# keccak of Deposited(address,address,uint256,uint256)
ENTRYPOINT_DEPOSITED_TOPIC: Final = b"\xf5h\x1f\x9d\r\xb1\xb9\x11\xac\x18\xee\x83\xd5\x15\xa1\xcf\x10Q\x85:\x9e\xaeA\x83\x16\xa2\xfd\xf7\xde\xa4'\xc5"  # noqa: E501
# keccak of WithdrawalRelayed(address,address,address,uint256,uint256)
WITHDRAWAL_RELAYED_TOPIC: Final = b'\xe9\xb6xD\xa7\xbbnj\xc9^\x8a\r\xe0.DH\xdb\xb0\xc9F\x0b\xe9\x19CH\xe4\xbb\xacm\x13\xc2\xcf'  # noqa: E501
# keccak of Ragequit(address,uint256,uint256,uint256)
RAGEQUIT_TOPIC: Final = b'\xd2\xb3\xe8h\xae\x10\x11\x067\x1f+\xd9:\xbc\x8dZM\xe4\x88\xb9\xfeG\xed\x12,#bZ\xa7\x17/\x13'  # noqa: E501
# keccak of Ragequit(address,address,uint256,uint256,uint256,uint256)
V2_POOL_RAGEQUIT_TOPIC: Final = b'PtU\xb2\\\x1aE\x95r\r\xa5\xb6\xa8\xf6\xb7nJ\xa3m\xb9\x87\xa6;G&a\x12\xd3\xcb\xf2\xe1\x03'  # noqa: E501
# keccak of Relayed(address,address,uint256,address,uint256,uint256)
V2_RELAYED_TOPIC: Final = b'\xd1\xb9D_4\x1f\xec(\x0e\x18\x12*;3\xb6\xfet\x9a\xcc\xb3\x95T\x1a\xcf] %P\xb3\xa9\xb3 '  # noqa: E501
# keccak of RelayedBatch(address,address,uint256,address,uint256,uint256,uint256)
V2_RELAYED_BATCH_TOPIC: Final = b'\xc2\xd3&WL\xbbv\xa0\xa6_\xd6\x0e\x94\x98\x1b\xa7PA\xb9\xf4\x7f/W`\x88\x15F\xaa\xc1\x1e\xd8\x1a'  # noqa: E501
# keccak of WithdrawnToUnderlying(address,address,address,uint256,uint256,address,uint256,uint256,uint256)  # noqa: E501
V2_PP_ROUTER_WITHDRAWN_TOPIC: Final = b'\xa3\xd5\xae2\x84\xdf\x0c,\xdd\xe6\xee\x0f\x85i[\xfc\x81R\x98\xb1$\xdd\xe2\\\xab\xa7/\xd1\xe2\xc4\x91\xb7'  # noqa: E501

L2_ENTRYPOINT: Final = string_to_evm_address('0x44192215FEd782896BE2CE24E0Bfbf0BF825d15E')
L2_NATIVE_POOL: Final = string_to_evm_address('0x4626A182030D9e98b13f690FFF3C443191a918ff')

V2_ENTRYPOINT: Final = string_to_evm_address('0xca1e072236D231130059eeA6Bfceb7F4e9a1F0C3')
V2_POOL_VAULT: Final = string_to_evm_address('0x0Eb42804BF897662aF851370eaeAdcDBEC1b97ed')
V2_RELAY: Final = string_to_evm_address('0x01a8Fa4dbb60187aD8d3c3d08E7Fb8C14198A461')


class PrivacyPoolsDeployment(NamedTuple):
    entrypoint: ChecksumEvmAddress | None
    native_pool: ChecksumEvmAddress | None
    token_pools: dict[ChecksumEvmAddress, ChecksumEvmAddress]
    v2_routers: dict[ChecksumEvmAddress, ChecksumEvmAddress | None]


PRIVACY_POOLS_DEPLOYMENTS: Final[dict[ChainID, PrivacyPoolsDeployment]] = {
    ChainID.ETHEREUM: PrivacyPoolsDeployment(
        entrypoint=string_to_evm_address('0x6818809EefCe719E480a7526D76bD3e561526b46'),
        native_pool=string_to_evm_address('0xF241d57C6DebAe225c0F2e6eA1529373C9A9C9fB'),
        token_pools={
            string_to_evm_address('0x05e4DBD71B56861eeD2Aaa12d00A797F04B5D3c0'): string_to_evm_address('0xdC035D45d973E3EC169d2276DDab16f1e407384F'),  # USDS  # noqa: E501
            string_to_evm_address('0xBBdA2173CDFEA1c3bD7F2908798F1265301d750c'): string_to_evm_address('0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD'),  # sUSDS  # noqa: E501
            string_to_evm_address('0x1c31C03B8CB2EE674D0F11De77135536db828257'): string_to_evm_address('0x6B175474E89094C44Da98b954EedeAC495271d0F'),  # DAI  # noqa: E501
            string_to_evm_address('0xe859C0bD25f260BaEE534Fb52e307D3b64D24572'): string_to_evm_address('0xdAC17F958D2ee523a2206206994597C13D831ec7'),  # USDT  # noqa: E501
            string_to_evm_address('0xb419c2867aB3CBc78921660cB95150d95A94ce86'): string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),  # USDC  # noqa: E501
            string_to_evm_address('0x1A604E9DFa0EFDC7FFda378AF16Cb81243b61633'): string_to_evm_address('0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0'),  # wstETH  # noqa: E501
            string_to_evm_address('0xF973f4B180A568157Cd7A0E6006449139E6Bfc32'): string_to_evm_address('0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599'),  # WBTC  # noqa: E501
            string_to_evm_address('0xe6D36B33b00A7C0cB0C2a8d39D07e7dB0c526Abc'): string_to_evm_address('0x4c9EDD5852cd905f086C759E8383e09bff1E68B3'),  # USDe  # noqa: E501
            string_to_evm_address('0xc0A8Bc0F4F982b4d4f1fFae8F4FCCb58c9B29c98'): string_to_evm_address('0x8d0D000Ee44948FC98c9B98A4FA4921476f08B0d'),  # USD1  # noqa: E501
            string_to_evm_address('0xC6C769fac7AABEadd31a03fAe5Ca0Ec5B4C50f84'): string_to_evm_address('0xCAcd6fd266aF91b8AeD52aCCc382b4e165586E29'),  # frxUSD  # noqa: E501
            string_to_evm_address('0x7d2959bCFb936a84531518e8391DdBa844e03ebE'): string_to_evm_address('0xDcEe70654261AF21C44c093C300eD3Bb97b78192'),  # WOETH  # noqa: E501
            string_to_evm_address('0xD14F4B36E1D1D98c218db782c49149876042BC56'): string_to_evm_address('0x085780639CC2cACd35E474e71f4d000e2405d8f6'),  # fxUSD  # noqa: E501
            string_to_evm_address('0xb4b5Fd38Fd4788071d7287e3cB52948e0d10b23E'): string_to_evm_address('0x6440f144b7e50D6a8439336510312d2F54beB01D'),  # BOLD  # noqa: E501
        },
        v2_routers={
            string_to_evm_address('0xe76E793d776c1e207aD7a7fa7C57d27420d85110'): string_to_evm_address('0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48'),  # ppUSDC -> USDC  # noqa: E501
            string_to_evm_address('0x13a0b86bac3e0C29bd64fED7BCD2EE84f371f41C'): string_to_evm_address('0xdAC17F958D2ee523a2206206994597C13D831ec7'),  # ppUSDT -> USDT  # noqa: E501
            string_to_evm_address('0x77613D670BB9fD48A9898D0eac8ebf21B566F960'): None,  # ppETH -> ETH (native mode)  # noqa: E501
        },
    ),
    ChainID.OPTIMISM: PrivacyPoolsDeployment(
        entrypoint=L2_ENTRYPOINT,
        native_pool=L2_NATIVE_POOL,
        token_pools={
            string_to_evm_address('0xe4410f6827FA04cE096975D07A9924ABb65316e3'): string_to_evm_address('0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),  # USDC  # noqa: E501
        },
        v2_routers={
            string_to_evm_address('0xaaE55aFcF94c1604C5713CD19510c5140e8Afa0e'): string_to_evm_address('0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85'),  # ppUSDC -> USDC  # noqa: E501
            string_to_evm_address('0x19918499f1d06162A18B208cA4c97032A828dF0a'): string_to_evm_address('0x94b008aA00579c1307B0EF2c499aD98a8ce58e58'),  # ppUSDT -> USDT  # noqa: E501
            string_to_evm_address('0xc0FBB5D5936a6f089C1B30Ff0Fd0BEAd27b9F766'): None,  # ppETH -> ETH (native mode)  # noqa: E501
        },
    ),
    ChainID.BASE: PrivacyPoolsDeployment(
        entrypoint=L2_ENTRYPOINT,
        native_pool=L2_NATIVE_POOL,
        token_pools={},
        v2_routers={
            string_to_evm_address('0xaaE55aFcF94c1604C5713CD19510c5140e8Afa0e'): string_to_evm_address('0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'),  # ppUSDC -> USDC  # noqa: E501
            string_to_evm_address('0xc0FBB5D5936a6f089C1B30Ff0Fd0BEAd27b9F766'): None,  # ppETH -> ETH (native mode)  # noqa: E501
        },
    ),
    ChainID.BINANCE_SC: PrivacyPoolsDeployment(
        entrypoint=L2_ENTRYPOINT,
        native_pool=L2_NATIVE_POOL,
        token_pools={
            string_to_evm_address('0x2ad9802Dc8b9b4022aDED1C6c8A7261970D84855'): string_to_evm_address('0x55d398326f99059fF775485246999027B3197955'),  # USDT  # noqa: E501
        },
        v2_routers={
            string_to_evm_address('0x9929Ad2Edc2E0B5D59C3f5b2910812D0c8b84E16'): string_to_evm_address('0x55d398326f99059fF775485246999027B3197955'),  # ppUSDT -> USDT  # noqa: E501
        },
    ),
    ChainID.ARBITRUM_ONE: PrivacyPoolsDeployment(
        entrypoint=L2_ENTRYPOINT,
        native_pool=L2_NATIVE_POOL,
        token_pools={
            string_to_evm_address('0xA63e0bdc3A193d1E6e7c9bE72CB502BE4B7fC244'): string_to_evm_address('0x252b965400862d94BDa35FeCF7Ee0f204a53Cc36'),  # yUSND  # noqa: E501
            string_to_evm_address('0x3706e38af05bf0158BCdbB46239f8289980b093f'): string_to_evm_address('0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),  # USDC  # noqa: E501
        },
        v2_routers={
            string_to_evm_address('0xaaE55aFcF94c1604C5713CD19510c5140e8Afa0e'): string_to_evm_address('0xaf88d065e77c8cC2239327C5EDb3A432268e5831'),  # ppUSDC -> USDC  # noqa: E501
            string_to_evm_address('0x19918499f1d06162A18B208cA4c97032A828dF0a'): string_to_evm_address('0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9'),  # ppUSDT -> USDT  # noqa: E501
            string_to_evm_address('0xc0FBB5D5936a6f089C1B30Ff0Fd0BEAd27b9F766'): None,  # ppETH -> ETH (native mode)  # noqa: E501
        },
    ),
    ChainID.ROBINHOOD: PrivacyPoolsDeployment(
        entrypoint=None,
        native_pool=None,
        token_pools={},
        v2_routers={},
    ),
}
