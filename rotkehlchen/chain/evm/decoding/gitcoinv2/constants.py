from typing import Final

from eth_typing.abi import ABI, ABIEvent

VOTED: Final = b'\x00d\xca\xa7?\x1dY\xb6\x9a\xdb\xebeeK\x0f\tSYy\x94\xe4$\x1e\xe2F\x0bV\x0b\x8de\xaa\xa2'  # example: https://etherscan.io/tx/0x71fc406467f342f5801560a326aa29ac424381daf17cc04b5573960425ba605b#eventlog  # noqa: E501
VOTED_WITH_ORIGIN: Final = b'\xbf5\xc00\x17\x8a\x1eg\x8c\x82\x96\xa4\xe5\x08>\x90!\xa2L\x1a\x1d\xef\xa5\xbf\xbd\xfd\xe7K\xce\xcf\xa3v'  # noqa: E501 # example: https://optimistic.etherscan.io/tx/0x08685669305ee26060a5a78ae70065aec76d9e62a35f0837c291fb1232f33601#eventlog
VOTED_WITHOUT_APPLICATION_IDX: Final = b'A\x82\xeb\x95\xd4\x86\xb4/\xdd\xce\xa2%\x16/\x9a_\x93\xb0m\xfe\xbe\xdd\xf5\x81\x9d\x0fW\xf2\xc6\xaf>\x1b'  # noqa: E501 # example: 0xdcb6d2282b34a3cb7637ac65d8b7f1d0e8f2bc149379767f0b6f9ba2afa8a359
PROJECT_CREATED: Final = b'c\xc9/\x95\x05\xd4 \xbf\xf61\xcb\x9d\xf3;\xe9R\xbd\xc1\x1e!\x18\xda6\xa8P\xb4>k\xccL\xe4\xde'  # noqa: E501
METADATA_UPDATED: Final = b'\xf9,&9\xc2]j"\xc3\x8emk)?t\xa9\xb2$\x91\';\x1d\xbbg\xfc\x12U"&\x96\xbe['  # noqa: E501
NEW_PROJECT_APPLICATION_3ARGS: Final = b'\xcay&"\x04c%\xe9\xcdN$\xb4\x90\xcb\x00\x0e\xf7*\xce\xa3\xa1R\x84\xef\xc1N\xe7\t0z^\x00'  # noqa: E501
NEW_PROJECT_APPLICATION_2ARGS: Final = b'\xecy?\xe7\x04\xd3@\xd9b\xcd\x02\xd8\x1a\xd5@E\xe7\xce\xeaq:\xcaN1\xc7\xc5\xc4>=\xcb\x19*'  # noqa: E501
FUNDS_DISTRIBUTED: Final = b'z\x0b2\xf6\x04\xa8\xc9C&2(a\x03\x9aD\xb7\xedxbL\xf2 \xba\x8bXj$G\xaf\r\x9c\x9b'  # noqa: E501
ALLOCATED: Final = b'\xdc\x9d@v\x03\x08U}\x13w\xc2\xfe|\x98J\xce\x9e\xb0-#\xb6\n_o&\xbeb\xc5$1\xbc8'  # noqa: E501
REGISTERED: Final = b'\xa1\x970n=\xd5IJa\xa6\x958\x1a\xa8\t\xa5;\x8e7zh^\x84\xe4\x04\xa8]Z\x8d\xa6\xccb'  # noqa: E501


GET_RECIPIENT_ABI: Final[ABI] = [{'inputs': [{'name': '_recipientId', 'type': 'address'}], 'name': 'getRecipient', 'outputs': [{'components': [{'name': 'useRegistryAnchor', 'type': 'bool'}, {'name': 'recipientAddress', 'type': 'address'}, {'components': [{'name': 'protocol', 'type': 'uint256'}, {'name': 'pointer', 'type': 'string'}], 'name': 'metadata', 'type': 'tuple'}], 'name': 'recipient', 'type': 'tuple'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501


REGISTERED_ABI: Final[ABIEvent] = {'anonymous': False, 'inputs': [{'indexed': True, 'name': 'recipientId', 'type': 'address'}, {'indexed': False, 'name': 'data', 'type': 'bytes'}, {'indexed': False, 'name': 'sender', 'type': 'address'}], 'name': 'Registered', 'type': 'event'}  # noqa: E501
