from typing import Final

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_GEARBOX: Final = 'gearbox'
GEARBOX_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_GEARBOX,
    label='Gearbox',
    image='gearbox.svg',
)
ADD_LIQUIDITY: Final = b'\xd2I\x1a\x9bO\xe8\x1a|\xd4Q\x1e\x8b{wC\x95\x1b\x06\x1d\xad[\xed}\xa8\xa7y[\x08\x0e\xe0\x8c~'  # noqa: E501
REMOVE_LIQUIDITY: Final = b'\xd8\xae\x9b\x9b\xa8\x9ec{\xcbf\xa6\x9a\xc9\x1e\x8fh\x80\x18\xe8\x1do\x92\xc5~\x02"d%\xc8\xef\xbd\xf6'  # noqa: E501
DEPOSIT: Final = b'\xdc\xbc\x1c\x05$\x0f1\xff:\xd0g\xef\x1e\xe3\\\xe4\x99wbu.:\tR\x84uED\xf4\xc7\t\xd7'  # noqa: E501
WITHDRAW: Final = b'\xfb\xdey} \x1ch\x1b\x91\x05e)\x11\x9e\x0b\x02@|{\xb9jJ,u\xc0\x1f\xc9fr2\xc8\xdb'  # noqa: E501
GEARBOX_CONTRACTS_REGISTER: Final = string_to_evm_address('0xA50d4E7D8946a7c90652339CDBd262c375d54D99')  # noqa: E501
GEARBOX_DATA_COMPRESSOR: Final = string_to_evm_address('0xc0101abAFce0BD3de10aa1F3dd827672B150436E')  # noqa: E501
