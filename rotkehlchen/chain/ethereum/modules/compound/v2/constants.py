from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import (
    A_AAVE,
    A_BAT,
    A_COMP,
    A_DAI,
    A_ETH,
    A_LINK,
    A_MKR,
    A_REP,
    A_SAI,
    A_SUSHI,
    A_TUSD,
    A_UNI,
    A_USDC,
    A_USDT,
    A_WBTC,
    A_YFI,
    A_ZRX,
)
from rotkehlchen.types import ChecksumEvmAddress

COMPTROLLER_PROXY_ADDRESS = string_to_evm_address('0x3d9819210A31b4961b30EF54bE2aeD79B9c9Cd3B')
COMPOUND_REWARDS_ADDRESS = string_to_evm_address('0x1B0e765F6224C21223AeA2af16c1C46E38885a40')
CPT_COMPOUND = 'compound'
CTOKEN_MAPPING: dict[ChecksumEvmAddress, Asset] = {
    string_to_evm_address('0xe65cdB6479BaC1e22340E4E755fAE7E509EcD06c'): A_AAVE,
    string_to_evm_address('0x6C8c6b02E7b2BE14d4fA6022Dfd6d75921D90E4E'): A_BAT,
    string_to_evm_address('0x70e36f6BF80a52b3B46b3aF8e106CC0ed743E8e4'): A_COMP,
    string_to_evm_address('0x5d3a536E4D6DbD6114cc1Ead35777bAB948E3643'): A_DAI,
    string_to_evm_address('0x4Ddc2D193948926D02f9B1fE9e1daa0718270ED5'): A_ETH,
    string_to_evm_address('0x7713DD9Ca933848F6819F38B8352D9A15EA73F67'): Asset('eip155:1/erc20:0x956F47F50A910163D8BF957Cf5846D573E7f87CA'),  # FEI  # noqa: E501
    string_to_evm_address('0xFAce851a4921ce59e912d19329929CE6da6EB0c7'): A_LINK,
    string_to_evm_address('0x95b4eF2869eBD94BEb4eEE400a99824BF5DC325b'): A_MKR,
    string_to_evm_address('0x158079Ee67Fce2f58472A96584A73C7Ab9AC95c1'): A_REP,
    string_to_evm_address('0xF5DCe57282A584D2746FaF1593d3121Fcac444dC'): A_SAI,
    string_to_evm_address('0x4B0181102A0112A2ef11AbEE5563bb4a3176c9d7'): A_SUSHI,
    string_to_evm_address('0x12392F67bdf24faE0AF363c24aC620a2f67DAd86'): A_TUSD,
    string_to_evm_address('0x35A18000230DA775CAc24873d00Ff85BccdeD550'): A_UNI,
    string_to_evm_address('0x39AA39c021dfbaE8faC545936693aC917d5E7563'): A_USDC,
    string_to_evm_address('0x041171993284df560249B57358F931D9eB7b925D'): Asset('eip155:1/erc20:0x1456688345527bE1f37E9e627DA0837D6f08C925'),  # USDP  # noqa: E501
    string_to_evm_address('0xf650C3d88D12dB855b8bf7D11Be6C55A4e07dCC9'): A_USDT,
    string_to_evm_address('0xC11b1268C1A384e55C48c2391d8d480264A3A7F4'): A_WBTC,
    string_to_evm_address('0xccF4429DB6322D5C611ee964527D42E5d685DD6a'): A_WBTC,  # v2
    string_to_evm_address('0x80a2AE356fc9ef4305676f7a3E2Ed04e12C33946'): A_YFI,
    string_to_evm_address('0xB3319f5D18Bc0D84dD1b4825Dcde5d5f7266d407'): A_ZRX,
}  # information from https://docs.compound.finance/v2/
