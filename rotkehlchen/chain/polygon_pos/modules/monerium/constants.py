from typing import Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address

POLYGON_MONERIUM_LEGACY_ADDRESSES: Final = {
    string_to_evm_address('0x18ec0A6E18E5bc3784fDd3a3634b31245ab704F6'),  # legacy EURe
    string_to_evm_address('0x75792CBDb361d80ba89271a079EfeE62c29FA324'),  # legacy GBPe
    string_to_evm_address('0x64E97c1a6535afD4a313eF46F88A64a34250B719'),  # legacy USDe
    string_to_evm_address('0xf1bBf27A9D659D326efBfa5D284EBaeFB803983D'),  # legacy ISKe
}

POLYGON_MONERIUM_ADDRESSES: Final = POLYGON_MONERIUM_LEGACY_ADDRESSES | {
    string_to_evm_address('0xE0aEa583266584DafBB3f9C3211d5588c73fEa8d'),  # EURe
    string_to_evm_address('0x646BEea7a02FdAdA34c8e118949fE32350aB2206'),  # GBPe
    string_to_evm_address('0x91e2B584908C2807EFc9F846E0C2A1fe875C5141'),  # USDe
    string_to_evm_address('0xd053fc09e8F05A43Da4ECC40a750559C938C8131'),  # ISKe
}

V1_TO_V2_MONERIUM_MAPPINGS: Final = {
    'eip155:137/erc20:0x18ec0A6E18E5bc3784fDd3a3634b31245ab704F6': Asset('eip155:137/erc20:0xE0aEa583266584DafBB3f9C3211d5588c73fEa8d'),  # noqa: E501
    'eip155:137/erc20:0x75792CBDb361d80ba89271a079EfeE62c29FA324': Asset('eip155:137/erc20:0x646BEea7a02FdAdA34c8e118949fE32350aB2206'),  # noqa: E501
    'eip155:137/erc20:0x64E97c1a6535afD4a313eF46F88A64a34250B719': Asset('eip155:137/erc20:0x91e2B584908C2807EFc9F846E0C2A1fe875C5141'),  # noqa: E501
    'eip155:137/erc20:0xf1bBf27A9D659D326efBfa5D284EBaeFB803983D': Asset('eip155:137/erc20:0xd053fc09e8F05A43Da4ECC40a750559C938C8131'),  # noqa: E501
}
