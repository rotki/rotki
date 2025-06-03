from typing import Final

from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_DIGIXDAO: Final = 'digixdao'
DIGIX_DGD_ETH_REFUND_CONTRACT: Final = string_to_evm_address('0x23Ea10CC1e6EBdB499D24E45369A35f43627062f')  # noqa: E501
A_DGD: Final = Asset('eip155:1/erc20:0xE0B7927c4aF23765Cb51314A0E0521A9645F0E2A')
