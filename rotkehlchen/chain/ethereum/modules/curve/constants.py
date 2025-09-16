from typing import Final

from rotkehlchen.chain.evm.decoding.curve.constants import CURVE_SWAP_ROUTER_V1
from rotkehlchen.chain.evm.types import string_to_evm_address

GAUGE_BRIBE_V2: Final = string_to_evm_address('0x7893bbb46613d7a4FbcC31Dab4C9b823FfeE1026')
FEE_DISTRIBUTOR_3CRV: Final = string_to_evm_address('0xA464e6DCda8AC41e03616F95f4BC98a13b8922Dc')
FEE_DISTRIBUTOR_CRVUSD: Final = string_to_evm_address('0xD16d5eC345Dd86Fb63C6a9C43c517210F1027914')
VOTING_ESCROW: Final = string_to_evm_address('0x5f3b5DfEb7B28CDbD7FAba78963EE202a494e2A2')
CURVE_MINTER: Final = string_to_evm_address('0xd061D61a4d941c39E5453435B6345Dc261C2fcE0')
CLAIMED: Final = b'\x9c\xdc\xf2\xf7qL\xca5\x08\xc7\xf0\x11\x0b\x04\xa9\n\x80\xa3\xa8\xdd\x0e5\xde\x99h\x9d\xb7M(\xc58>'  # noqa: E501
VOTING_ESCROW_DEPOSIT: Final = b'Ef\xdf\xc2\x9fo\x11\xd1:A\x8c&\xa0+\xef|(\xba\xe7I\xd4\xdeG\xe4\xe6\xa7\xcd\xde\xa6s\rY'  # noqa: E501

GAUGE_BRIBE_V2_ASSETS: Final = [
    string_to_evm_address('0xD533a949740bb3306d119CC777fa900bA034cd52'),  # CRV
    string_to_evm_address('0x4e3FBD56CD56c3e72c1403e103b45Db9da5B9D2B'),  # CVX
    string_to_evm_address('0xdB25f211AB05b1c97D595516F45794528a807ad8'),  # EURS
    string_to_evm_address('0x090185f2135308BaD17527004364eBcC2D37e5F6'),  # SPELL
]

# Deposit contracts are retrieved from the links below Deposit<pool>:
# https://curve.readthedocs.io/ref-addresses.html#base-pools
# https://curve.readthedocs.io/ref-addresses.html#metapools
#
# The duplicates were found via Etherscan:
# https://etherscan.io/find-similar-contracts?a=0x35796DAc54f144DFBAD1441Ec7C32313A7c29F39
CURVE_DEPOSIT_CONTRACTS: Final = {
    string_to_evm_address('0x094d12e5b541784701FD8d65F11fc0598FBC6332'),  # curve usdn
    string_to_evm_address('0x35796DAc54f144DFBAD1441Ec7C32313A7c29F39'),  # curve usdn duplicate
    string_to_evm_address('0xB0a0716841F2Fc03fbA72A891B8Bb13584F52F2d'),  # curve ust
    string_to_evm_address('0x3c8cAee4E09296800f8D29A68Fa3837e2dae4940'),  # curve usdp
    string_to_evm_address('0xF1f85a74AD6c64315F85af52d3d46bF715236ADc'),  # curve usdk
    string_to_evm_address('0x6600e98b71dabfD4A8Cac03b302B0189Adb86Afb'),  # curve usdk duplicate
    string_to_evm_address('0xBE175115BF33E12348ff77CcfEE4726866A0Fbd5'),  # curve rsv
    string_to_evm_address('0x803A2B40c5a9BB2B86DD630B274Fa2A9202874C2'),  # curve musd
    string_to_evm_address('0x78CF256256C8089d68Cde634Cf7cDEFb39286470'),  # curve musd duplicate
    string_to_evm_address('0x1de7f0866e2c4adAC7b457c58Cc25c8688CDa1f2'),  # curve linkusd
    string_to_evm_address('0xF6bDc2619FFDA72c537Cd9605e0A274Dc48cB1C9'),  # curve linkusd duplicate  # noqa: E501
    string_to_evm_address('0x09672362833d8f703D5395ef3252D4Bfa51c15ca'),  # curve husd
    string_to_evm_address('0x0a53FaDa2d943057C47A301D25a4D9b3B8e01e8E'),  # curve husd duplicate
    string_to_evm_address('0x64448B78561690B70E17CBE8029a3e5c1bB7136e'),  # curve gusd
    string_to_evm_address('0x0aE274c98c0415C0651AF8cF52b010136E4a0082'),  # curve gusd duplicate
    string_to_evm_address('0x61E10659fe3aa93d036d099405224E4Ac24996d0'),  # curve dusd
    string_to_evm_address('0xbBC81d23Ea2c3ec7e56D39296F0cbB648873a5d3'),  # curve y
    string_to_evm_address('0xb6c057591E073249F2D9D88Ba59a46CFC9B59EdB'),  # curve busd
    string_to_evm_address('0xeB21209ae4C2c9FF2a86ACA31E123764A3B6Bc06'),  # curve compound
    string_to_evm_address('0xA50cCc70b6a011CffDdf45057E39679379187287'),  # curve pax
    string_to_evm_address('0xFCBa3E75865d2d561BE8D220616520c171F12851'),  # curve susd v2
    string_to_evm_address('0x331aF2E331bd619DefAa5DAc6c038f53FCF9F785'),  # curve zap
    string_to_evm_address('0xac795D2c97e60DF6a99ff1c814727302fD747a80'),  # curve usdt
    string_to_evm_address('0xC45b2EEe6e09cA176Ca3bB5f7eEe7C47bF93c756'),  # curve bbtc
    string_to_evm_address('0xd5BCf53e2C81e1991570f33Fa881c49EEa570C8D'),  # curve obtc
    string_to_evm_address('0x11F419AdAbbFF8d595E7d5b223eee3863Bb3902C'),  # curve pbtc
    string_to_evm_address('0xaa82ca713D94bBA7A89CEAB55314F9EfFEdDc78c'),  # curve tbtc
    string_to_evm_address('0xA79828DF1850E8a3A3064576f380D90aECDD3359'),  # curve 3pool
    string_to_evm_address('0x08780fb7E580e492c1935bEe4fA5920b94AA95Da'),  # curve fraxusdc
    string_to_evm_address('0x7AbDBAf29929e7F8621B757D2a7c04d78d633834'),  # curve sbtc
    string_to_evm_address('0xA2d40Edbf76C6C0701BA8899e2d059798eBa628e'),  # curve sbtc2
}
DEPOSIT_AND_STAKE_ZAP: Final = string_to_evm_address('0x56C526b0159a258887e0d79ec3a80dfb940d0cD7')
GAUGE_CONTROLLER: Final = string_to_evm_address('0x2F50D538606Fa9EDD2B11E2446BEb18C9D5846bB')
CURVE_SWAP_ROUTERS: Final = {
    string_to_evm_address('0x99a58482BD75cbab83b27EC03CA68fF489b5788f'),
    CURVE_SWAP_ROUTER_V1,
    string_to_evm_address('0x16C6521Dff6baB339122a0FE25a9116693265353'),  # Curve Router v1.1
    string_to_evm_address('0x45312ea0eFf7E09C83CBE249fa1d7598c4C8cd4e'),  # Curve Router v1.2
}
AAVE_POOLS: Final = {
    string_to_evm_address('0xDeBF20617708857ebe4F679508E7b7863a8A8EeE'),  # aDAI + aUSDC + aUSDT
    string_to_evm_address('0xEB16Ae0052ed37f479f7fe63849198Df1765a733'),  # aDAI + aSUSD
}
