from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

GITCOIN_GOVERNOR_ALPHA: Final = string_to_evm_address('0xDbD27635A534A3d3169Ef0498beB56Fb9c937489')
GITCOIN_GRANTS_OLD1: Final = string_to_evm_address('0xdf869FAD6dB91f437B59F1EdEFab319493D4C4cE')
GITCOIN_GC15_MATCHING: Final = string_to_evm_address('0xC8AcA0b50F3Ca9A0cBe413d8a110a7aab7d4C1aE')

FUNDS_CLAIMED: Final = b'\xa4\xebP\x10;\x05\x91\xfe\xb0\xbc\x91?G\x9d\x92\xaf^\xb7\xea3\xe8\xc3\x97\xb4\x9b\xabR\xcej\xf2l\xb5'  # noqa: E501
