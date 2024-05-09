from typing import Final

from rotkehlchen.chain.evm.decoding.hop.structures import HopBridgeEventData
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_DAI, A_ETH, A_ETH_MATIC, A_SNX, A_SUSD, A_USDC, A_USDT

BRIDGES: Final = {
    string_to_evm_address('0xb8901acB165ed027E32754E0FFe830802919727f'): HopBridgeEventData(
        identifier=A_ETH.identifier,
    ), string_to_evm_address('0x3666f603Cc164936C1b87e207F36BEBa4AC5f18a'): HopBridgeEventData(
        identifier=A_USDC.identifier,
    ), string_to_evm_address('0x3E4a3a4796d16c0Cd582C382691998f7c06420B6'): HopBridgeEventData(
        identifier=A_USDT.identifier,
    ), string_to_evm_address('0x22B1Cbb8D98a01a3B71D034BB899775A76Eb1cc2'): HopBridgeEventData(
        identifier=A_ETH_MATIC.identifier,
    ), string_to_evm_address('0x3d4Cc8A61c7528Fd86C55cfe061a78dCBA48EDd1'): HopBridgeEventData(
        identifier=A_DAI.identifier,
    ), string_to_evm_address('0x914f986a44AcB623A277d6Bd17368171FCbe4273'): HopBridgeEventData(
        identifier='eip155:1/erc20:0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC',
    ), string_to_evm_address('0x893246FACF345c99e4235E5A7bbEE7404c988b96'): HopBridgeEventData(
        identifier=A_SNX.identifier,
    ), string_to_evm_address('0x36443fC70E073fe9D50425f82a3eE19feF697d62'): HopBridgeEventData(
        identifier=A_SUSD.identifier,
    ), string_to_evm_address('0x87269B23e73305117D0404557bAdc459CEd0dbEc'): HopBridgeEventData(
        identifier='eip155:1/erc20:0xae78736Cd615f374D3085123A210448E74Fc6393',
    ), string_to_evm_address('0xf074540eb83c86211F305E145eB31743E228E57d'): HopBridgeEventData(
        identifier='eip155:1/erc20:0xB0c7a3Ba49C7a6EaBa6cD4a96C55a1391070Ac9A',
    ),
}
