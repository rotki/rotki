from typing import Final

ADDR_CHANGED: Final = b'R\xd7\xd8a\xf0\x9a\xb3\xd2b9\xd4\x92\xe8\x96\x86)\xf9^\x9e1\x8c\xf0\xb7;\xfd\xdcD\x15"\xa1_\xd2'  # noqa: E501
CONTENT_HASH_CHANGED: Final = b'\xe3y\xc1bN\xd7\xe7\x14\xcc\t7R\x8a25\x9di\xd5(\x137vS\x13\xdb\xa4\xe0\x81\xb7-ux'  # noqa: E501
NEW_OWNER: Final = b'\xce\x04W\xfess\x1f\x82L\xc2r7ai#Q(\xc1\x18\xb4\x9d4H\x17A|m\x10\x8d\x15^\x82'
NEW_RESOLVER: Final = b'3W!\xb0\x18f\xdc#\xfb\xee\x8bk,{\x1e\x14\xd6\xf0\\(\xcd5\xa2\xc94#\x9f\x94\tV\x02\xa0'  # noqa: E501
TEXT_CHANGED_KEY_ONLY: Final = b'\xd8\xc93K\x1a\x9c/\x9d\xa3B\xa0\xa2\xb3&)\xc1\xa2)\xb6D]\xadx\x94\x7fgKDDJuP'  # noqa: E501
TEXT_CHANGED_KEY_ONLY_ABI: Final = '{"anonymous":false,"inputs":[{"indexed":true,"internalType":"bytes32","name":"node","type":"bytes32"},{"indexed":true,"internalType":"string","name":"indexedKey","type":"string"},{"indexed":false,"internalType":"string","name":"key","type":"string"}],"name":"TextChanged","type":"event"}'  # noqa: E501
TEXT_CHANGED_KEY_AND_VALUE: Final = b'D\x8b\xc0\x14\xf1Sg&\xcf\x8dT\xff=d\x81\xed<\xbch<%\x91\xca Bt\x00\x9a\xfa\t\xb1\xa1'  # noqa: E501
TEXT_CHANGED_KEY_AND_VALUE_ABI: Final = '{"anonymous":false,"inputs":[{"indexed":true,"internalType":"bytes32","name":"node","type":"bytes32"},{"indexed":true,"internalType":"string","name":"indexedKey","type":"string"},{"indexed":false,"internalType":"string","name":"key","type":"string"},{"indexed":false,"internalType":"string","name":"value","type":"string"}],"name":"TextChanged","type":"event"}'  # noqa: E501
