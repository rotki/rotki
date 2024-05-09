from typing import Final

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.hop.structures import HopBridgeEventData
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH

BRIDGES: Final = {
    string_to_evm_address('0x3749C4f034022c39ecafFaBA182555d4508caCCC'): HopBridgeEventData(
        identifier=A_ETH.identifier,
        amm_wrapper=string_to_evm_address('0x33ceb27b39d2Bb7D2e61F7564d3Df29344020417'),
        saddle_swap=string_to_evm_address('0x652d27c0F72771Ce5C76fd400edD61B406Ac6D97'),
    ), string_to_evm_address('0x0e0E3d2C5c292161999474247956EF542caBF8dd'): HopBridgeEventData(
        identifier='eip155:42161/erc20:0xFF970A61A04b1cA14834A43f5dE4533eBDDB5CC8',
        amm_wrapper=string_to_evm_address('0xe22D2beDb3Eca35E6397e0C6D62857094aA26F52'),
        saddle_swap=string_to_evm_address('0x10541b07d8Ad2647Dc6cD67abd4c03575dade261'),
    ), string_to_evm_address('0x72209Fe68386b37A40d6bCA04f78356fd342491f'): HopBridgeEventData(
        identifier='eip155:42161/erc20:0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9',
        amm_wrapper=string_to_evm_address('0xCB0a4177E0A60247C0ad18Be87f8eDfF6DD30283'),
        saddle_swap=string_to_evm_address('0x18f7402B673Ba6Fb5EA4B95768aABb8aaD7ef18a'),
    ), string_to_evm_address('0x7aC115536FE3A185100B2c4DE4cb328bf3A58Ba6'): HopBridgeEventData(
        identifier='eip155:42161/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1',
        amm_wrapper=string_to_evm_address('0xe7F40BF16AB09f4a6906Ac2CAA4094aD2dA48Cc2'),
        saddle_swap=string_to_evm_address('0xa5A33aB9063395A90CCbEa2D86a62EcCf27B5742'),
    ), string_to_evm_address('0x25FB92E505F752F730cAD0Bd4fa17ecE4A384266'): HopBridgeEventData(
        identifier='eip155:42161/erc20:0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC',
        amm_wrapper=ZERO_ADDRESS,
    ), string_to_evm_address('0xc315239cFb05F1E130E7E28E603CEa4C014c57f0'): HopBridgeEventData(
        identifier='eip155:42161/erc20:0xEC70Dcb4A1EFa46b8F2D97C310C9c4790ba5ffA8',
        amm_wrapper=string_to_evm_address('0x16e08C02e4B78B0a5b3A917FF5FeaeDd349a5a95'),
        saddle_swap=string_to_evm_address('0x0Ded0d521AC7B0d312871D18EA4FDE79f03Ee7CA'),
    ), string_to_evm_address('0xEa5abf2C909169823d939de377Ef2Bf897A6CE98'): HopBridgeEventData(
        identifier='eip155:42161/erc20:0x539bdE0d7Dbd336b79148AA742883198BBF60342',
        amm_wrapper=string_to_evm_address('0x50a3a623d00fd8b8a4F3CbC5aa53D0Bc6FA912DD'),
        hop_identifier='eip155:42161/erc20:0xB76e673EBC922b1E8f10303D0d513a9E710f5c4c',
        saddle_swap=string_to_evm_address('0xFFe42d3Ba79Ee5Ee74a999CAd0c60EF1153F0b82'),
    ),
}
