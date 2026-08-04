from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

if TYPE_CHECKING:
    from rotkehlchen.types import ChecksumEvmAddress

CPT_FRANKENCOIN: Final = 'frankencoin'
FRANKENCOIN_COUNTERPARTY_LABEL: Final = 'Frankencoin'
FRANKENCOIN_COUNTERPARTY_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_FRANKENCOIN,
    label=FRANKENCOIN_COUNTERPARTY_LABEL,
    image='frankencoin.svg',
)

ZCHF_ADDRESS: Final[dict[ChainID, ChecksumEvmAddress]] = {
    ChainID.ETHEREUM: string_to_evm_address('0xB58E61C3098d85632Df34EecfB899A1Ed80921cB'),
    ChainID.ARBITRUM_ONE: string_to_evm_address('0xB33c4255938de7A6ec1200d397B2b2F329397F9B'),
    ChainID.BASE: string_to_evm_address('0xD4dD9e2F021BB459D5A5f6c24C12fE09c5D45553'),
    ChainID.GNOSIS: string_to_evm_address('0xD4dD9e2F021BB459D5A5f6c24C12fE09c5D45553'),
    ChainID.POLYGON_POS: string_to_evm_address('0x02567e4b14b25549331fCEe2B56c647A8bAB16FD'),
    ChainID.AVALANCHE: string_to_evm_address('0xD4dD9e2F021BB459D5A5f6c24C12fE09c5D45553'),
    ChainID.OPTIMISM: string_to_evm_address('0x4F8a84C442F9675610c680990EdDb2CCDDB8aB6f'),
}
