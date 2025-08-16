from typing import Final

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.types import ChainID

CPT_GEARBOX: Final = 'gearbox'
GEARBOX_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_GEARBOX,
    label='Gearbox',
    image='gearbox.svg',
)
ADD_LIQUIDITY: Final = b'\xd2I\x1a\x9bO\xe8\x1a|\xd4Q\x1e\x8b{wC\x95\x1b\x06\x1d\xad[\xed}\xa8\xa7y[\x08\x0e\xe0\x8c~'  # noqa: E501
REMOVE_LIQUIDITY: Final = b'\xd8\xae\x9b\x9b\xa8\x9ec{\xcbf\xa6\x9a\xc9\x1e\x8fh\x80\x18\xe8\x1do\x92\xc5~\x02"d%\xc8\xef\xbd\xf6'  # noqa: E501
DEPOSIT_GEAR: Final = b'@\xc1\xc5\xee\xa4N\xd2\x91_Fz\xf4\xc2v\xc8 \xaf\x0e\xa6\x1e`\xce\xc9J\xe2\x18\xe2l\xe8\x8c\x9dX'  # noqa: E501
CLAIM_GEAR_WITHDRAWAL: Final = b'\x9e\xa8\x17\xed\\\xcbZ\x1e\xaf\xcdm\x01\xa8\x96\x03Vva][\xf2\xb5\x9a\x17\x98\x80\x1a5\xe0\rJ\xa1'  # noqa: E501

CHAIN_ID_TO_DATA_COMPRESSOR: Final = {
    ChainID.ETHEREUM: string_to_evm_address('0x104c4e209329524adb0febE8b6481346a6eB75C6'),
    ChainID.OPTIMISM: string_to_evm_address('0x2697e6Ddbf572df3403B2451b954762Fd22002F6'),
    ChainID.ARBITRUM_ONE: string_to_evm_address('0x88aa4FbF86392cBF6f6517790E288314DE03E181'),
}
