from typing import Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_SKY: Final = 'sky'
DAI_TO_USDS_CONTRACT: Final = string_to_evm_address('0x3225737a9Bbb6473CB4a45b7244ACa2BeFdB276A')
MKR_TO_SKY_CONTRACT: Final = string_to_evm_address('0xBDcFCA946b6CDd965f99a839e4435Bcdc1bc470B')
SUSDS_CONTRACT: Final = string_to_evm_address('0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD')
MIGRATION_ACTIONS_CONTRACT: Final = string_to_evm_address('0xf86141a5657Cf52AEB3E30eBccA5Ad3a8f714B89')  # noqa: E501
USDS_JOIN_ADDRESS: Final = string_to_evm_address('0x3C0f895007CA717Aa01c8693e59DF1e8C3777FEB')
LITE_PSM_USDC_A: Final = string_to_evm_address('0xf6e72Db5454dd049d0788e411b06CfAF16853042')
EXIT: Final = b'\xbc*g\xd4"\xc2h\xdao\xe4_>}\x19N\x1d\x98\x90m"\x1f\x1c\xfa\xd6*\\\x80\xf2\xcd \x9fL'  # noqa: E501

SKY_ASSET: Final = Asset('eip155:1/erc20:0x56072C95FAA701256059aa122697B133aDEd9279')
USDS_ASSET: Final = Asset('eip155:1/erc20:0xdC035D45d973E3EC169d2276DDab16f1e407384F')
SUSDS_ASSET: Final = Asset('eip155:1/erc20:0xa3931d71877C0E7a3148CB7Eb4463524FEc27fbD')

DAI_TO_USDS: Final = b'#\x88\x9d\xb6\xb2D\xd294M\xea\xc8\x8e\xc7x\x1d\x81\x0b8s\xfe299\xd1\xce\x0e\x8a\xc9VB5'  # noqa: E501
MKR_TO_SKY: Final = b'u\x1b\xfe\xaa+\xcc\xc5\x0e\xf1P\xef\xea\xf6^\xf7\x90\x18\xf1\xdda\xe4\x07\x8dI\x942)\xe3\x1e\xb8\xce\x1a'  # noqa: E501
BUY_GEM: Final = b'\x08]\x06\xec\xf4\xc3K#wg\xa3\x1c\x08\x88\xe1!\xd8\x95F\xa7\x7f\x18o\x19\x87\xc6\xb8q^\x1a\x8c\xaa'  # noqa: E501
SELL_GEM: Final = b'\xefu\xf5\xa4|\xc9\xa9)\x96\x87\x96\xce\xb8O\x19\xe7T\x16\x17\xb4W\x7f,"\x8e\xa9R\x00\xe1W \x81'  # noqa: E501
