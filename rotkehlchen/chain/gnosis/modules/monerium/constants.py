from typing import Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address

GNOSIS_MONERIUM_LEGACY_ADDRESSES: Final = {
    string_to_evm_address('0xcB444e90D8198415266c6a2724b7900fb12FC56E'),  # legacy EURe
    string_to_evm_address('0x5Cb9073902F2035222B9749F8fB0c9BFe5527108'),  # legacy GBPe
    string_to_evm_address('0x20E694659536C6B46e4B8BE8f6303fFCD8d1dF69'),  # legacy USDe
    string_to_evm_address('0xD8F84BF2E036A3c8E4c0e25ed2aAe0370F3CCca8'),  # legacy ISKe
}
GNOSIS_MONERIUM_ADDRESSES: Final = GNOSIS_MONERIUM_LEGACY_ADDRESSES | {
    string_to_evm_address('0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430'),  # EURe
    string_to_evm_address('0x8E34bfEC4f6Eb781f9743D9b4af99CD23F9b7053'),  # GBPe
    string_to_evm_address('0x50D1A74F4b6dcaCddD97fd442C0e22a4c97F2b7f'),  # USDe
    string_to_evm_address('0x614Bd419D3735C9eb51542C06e5Acc09a9953f61'),  # ISKe
}

V1_TO_V2_MONERIUM_MAPPINGS: Final = {
    'eip155:100/erc20:0xcB444e90D8198415266c6a2724b7900fb12FC56E': Asset('eip155:100/erc20:0x420CA0f9B9b604cE0fd9C18EF134C705e5Fa3430'),  # noqa: E501
    'eip155:100/erc20:0x5Cb9073902F2035222B9749F8fB0c9BFe5527108': Asset('eip155:100/erc20:0x8E34bfEC4f6Eb781f9743D9b4af99CD23F9b7053'),  # noqa: E501
    'eip155:100/erc20:0x20E694659536C6B46e4B8BE8f6303fFCD8d1dF69': Asset('eip155:100/erc20:0x50D1A74F4b6dcaCddD97fd442C0e22a4c97F2b7f'),  # noqa: E501
    'eip155:100/erc20:0xD8F84BF2E036A3c8E4c0e25ed2aAe0370F3CCca8': Asset('eip155:100/erc20:0x614Bd419D3735C9eb51542C06e5Acc09a9953f61'),  # noqa: E501
}
