from typing import Final

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_ENS: Final = 'ens'
ENS_CPT_DETAILS: Final = CounterpartyDetails(identifier=CPT_ENS, label='ens', image='ens.svg')

ENS_REGISTRAR_CONTROLLER_1: Final = string_to_evm_address('0x283Af0B28c62C092C9727F1Ee09c02CA627EB7F5')  # noqa: E501
ENS_REGISTRAR_CONTROLLER_2: Final = string_to_evm_address('0x253553366Da8546fC250F225fe3d25d0C782303b')  # noqa: E501
ENS_BASE_REGISTRAR_IMPLEMENTATION: Final = string_to_evm_address('0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85')  # noqa: E501
ENS_REGISTRY_WITH_FALLBACK: Final = string_to_evm_address('0x00000000000C2E074eC69A0dFb2997BA6C7d2e1e')  # noqa: E501
ENS_PUBLIC_RESOLVER_2_ADDRESS: Final = string_to_evm_address('0x4976fb03C32e5B8cfe2b6cCB31c09Ba78EBaBa41')  # noqa: E501
ENS_PUBLIC_RESOLVER_3_ADDRESS: Final = string_to_evm_address('0x231b0Ee14048e9dCcD1d247744d114a4EB5E8E63')  # noqa: E501
ENS_REVERSE_RESOLVER: Final = string_to_evm_address('0xA2C122BE93b0074270ebeE7f6b7292C7deB45047')
ENS_GOVERNOR: Final = string_to_evm_address('0x323A76393544d5ecca80cd6ef2A560C6a395b7E3')

NAME_RENEWED: Final = b'=\xa2L\x02E\x82\x93\x1c\xfa\xf8&}\x8e\xd2M\x13\xa8*\x80h\xd5\xbd3}0\xecE\xce\xa4\xe5\x06\xae'  # noqa: E501
NAME_RENEWED_ABI: Final = '{"anonymous":false,"inputs":[{"indexed":false,"internalType":"string","name":"name","type":"string"},{"indexed":true,"internalType":"bytes32","name":"label","type":"bytes32"},{"indexed":false,"internalType":"uint256","name":"cost","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"expires","type":"uint256"}],"name":"NameRenewed","type":"event"}'  # noqa: E501
NEW_RESOLVER: Final = b'3W!\xb0\x18f\xdc#\xfb\xee\x8bk,{\x1e\x14\xd6\xf0\\(\xcd5\xa2\xc94#\x9f\x94\tV\x02\xa0'  # noqa: E501
NAME_REGISTERED_SINGLE_COST: Final = b'\xcaj\xbb\xe9\xd7\xf1\x14"\xcbl\xa7b\x9f\xbfo\xe9\xef\xb1\xc6!\xf7\x1c\xe8\xf0+\x9f*#\x00\x97@O'  # noqa: E501
NAME_REGISTERED_SINGLE_COST_ABI: Final = '{"anonymous":false,"inputs":[{"indexed":false,"internalType":"string","name":"name","type":"string"},{"indexed":true,"internalType":"bytes32","name":"label","type":"bytes32"},{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":false,"internalType":"uint256","name":"cost","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"expires","type":"uint256"}],"name":"NameRegistered","type":"event"}'  # noqa: E501
NAME_REGISTERED_BASE_COST_AND_PREMIUM: Final = b"i\xe3\x7f\x15\x1e\xb9\x8a\ta\x8d\xda\xa8\x0c\x8c\xfa\xf1\xceY\x96\x86|H\x9fE\xb5U\xb4\x12'\x1e\xbf'"  # noqa: E501
NAME_REGISTERED_BASE_COST_AND_PREMIUM_ABI: Final = '{"anonymous":false,"inputs":[{"indexed":false,"internalType":"string","name":"name","type":"string"},{"indexed":true,"internalType":"bytes32","name":"label","type":"bytes32"},{"indexed":true,"internalType":"address","name":"owner","type":"address"},{"indexed":false,"internalType":"uint256","name":"baseCost","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"premium","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"expires","type":"uint256"}],"name":"NameRegistered","type":"event"}'  # noqa: E501
TEXT_CHANGED_KEY_ONLY: Final = b'\xd8\xc93K\x1a\x9c/\x9d\xa3B\xa0\xa2\xb3&)\xc1\xa2)\xb6D]\xadx\x94\x7fgKDDJuP'  # noqa: E501
TEXT_CHANGED_KEY_ONLY_ABI: Final = '{"anonymous":false,"inputs":[{"indexed":true,"internalType":"bytes32","name":"node","type":"bytes32"},{"indexed":true,"internalType":"string","name":"indexedKey","type":"string"},{"indexed":false,"internalType":"string","name":"key","type":"string"}],"name":"TextChanged","type":"event"}'  # noqa: E501
TEXT_CHANGED_KEY_AND_VALUE: Final = b'D\x8b\xc0\x14\xf1Sg&\xcf\x8dT\xff=d\x81\xed<\xbch<%\x91\xca Bt\x00\x9a\xfa\t\xb1\xa1'  # noqa: E501
TEXT_CHANGED_KEY_AND_VALUE_ABI: Final = '{"anonymous":false,"inputs":[{"indexed":true,"internalType":"bytes32","name":"node","type":"bytes32"},{"indexed":true,"internalType":"string","name":"indexedKey","type":"string"},{"indexed":false,"internalType":"string","name":"key","type":"string"},{"indexed":false,"internalType":"string","name":"value","type":"string"}],"name":"TextChanged","type":"event"}'  # noqa: E501
CONTENT_HASH_CHANGED: Final = b'\xe3y\xc1bN\xd7\xe7\x14\xcc\t7R\x8a25\x9di\xd5(\x137vS\x13\xdb\xa4\xe0\x81\xb7-ux'  # noqa: E501
NEW_OWNER: Final = b'\xce\x04W\xfess\x1f\x82L\xc2r7ai#Q(\xc1\x18\xb4\x9d4H\x17A|m\x10\x8d\x15^\x82'
ADDR_CHANGED: Final = b'R\xd7\xd8a\xf0\x9a\xb3\xd2b9\xd4\x92\xe8\x96\x86)\xf9^\x9e1\x8c\xf0\xb7;\xfd\xdcD\x15"\xa1_\xd2'  # noqa: E501
