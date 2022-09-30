from rotkehlchen.assets.exchanges_mappings.common import COMMON_ASSETS_MAPPINGS
from rotkehlchen.constants.resolver import evm_address_to_identifier
from rotkehlchen.types import ChainID, EvmTokenKind

WORLD_TO_BLOCKFI = COMMON_ASSETS_MAPPINGS | {
    evm_address_to_identifier('0xB8c77482e45F1F44dE1745F52C74426C631bDD52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BNB',  # noqa: E501
    evm_address_to_identifier('0xd559f20296FF4895da39b5bd9ADd54b442596a61', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'FTX',  # noqa: E501
    evm_address_to_identifier('0x3845badAde8e6dFF049820680d1F14bD3903a5d0', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'SAND',  # noqa: E501
    evm_address_to_identifier('0x0D8775F648430679A709E98d2b0Cb6250d2887EF', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BAT',  # noqa: E501
    evm_address_to_identifier('0xD533a949740bb3306d119CC777fa900bA034cd52', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'CRV',  # noqa: E501
    evm_address_to_identifier('0xF629cBd94d3791C9250152BD8dfBDF380E2a3B9c', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'ENJ',  # noqa: E501
    evm_address_to_identifier('0x4Fabb145d64652a948d72533023f6E7A623C7C53', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'BUSD',  # noqa: E501
    evm_address_to_identifier('0x1456688345527bE1f37E9e627DA0837D6f08C925', ChainID.ETHEREUM, EvmTokenKind.ERC20): 'PAX',  # noqa: E501
}
