from typing import Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_SKY: Final = 'sky'
DAI_TO_USDS_CONTRACT: Final = string_to_evm_address('0x3225737a9Bbb6473CB4a45b7244ACa2BeFdB276A')
MKR_TO_SKY_CONTRACT: Final = string_to_evm_address('0xBDcFCA946b6CDd965f99a839e4435Bcdc1bc470B')
SUSDS_CONTRACT: Final = string_to_evm_address('0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD')
MIGRATION_ACTIONS_CONTRACT: Final = string_to_evm_address('0xf86141a5657Cf52AEB3E30eBccA5Ad3a8f714B89')  # noqa: E501

SKY_ASSET: Final = Asset('eip155:1/erc20:0x56072C95FAA701256059aa122697B133aDEd9279')
USDS_ASSET: Final = Asset('eip155:1/erc20:0xdC035D45d973E3EC169d2276DDab16f1e407384F')
SUSDS_ASSET: Final = Asset('eip155:1/erc20:0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD')

DAI_TO_USDS: Final = b'#\x88\x9d\xb6\xb2D\xd294M\xea\xc8\x8e\xc7x\x1d\x81\x0b8s\xfe299\xd1\xce\x0e\x8a\xc9VB5'  # noqa: E501
MKR_TO_SKY: Final = b'u\x1b\xfe\xaa+\xcc\xc5\x0e\xf1P\xef\xea\xf6^\xf7\x90\x18\xf1\xdda\xe4\x07\x8dI\x942)\xe3\x1e\xb8\xce\x1a'  # noqa: E501

DEPOSIT_USDS: Final = b'\xdc\xbc\x1c\x05$\x0f1\xff:\xd0g\xef\x1e\xe3\\\xe4\x99wbu.:\tR\x84uED\xf4\xc7\t\xd7'  # noqa: E501
WITHDRAW_USDS: Final = b'\xfb\xdey} \x1ch\x1b\x91\x05e)\x11\x9e\x0b\x02@|{\xb9jJ,u\xc0\x1f\xc9fr2\xc8\xdb'  # noqa: E501
