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

# TODO: Replace these placeholders with the actual ZCHF deployment addresses.
ZCHF_ADDRESS: Final[dict[ChainID, ChecksumEvmAddress]] = {
    ChainID.ETHEREUM: string_to_evm_address('0x0000000000000000000000000000000000000001'),
    ChainID.ARBITRUM_ONE: string_to_evm_address('0x0000000000000000000000000000000000000002'),
    ChainID.BASE: string_to_evm_address('0x0000000000000000000000000000000000000003'),
}
