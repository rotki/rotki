from typing import Final

from eth_typing.abi import ABI

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_JUICEBOX: Final = 'juicebox'
PAY_SIGNATURE: Final = b'\x131a\xf1\xc9\x16\x14\x88\xf7w\xab\x9a&\xaa\xe9\x1dG\xc0\xd9\xa3\xfa\xfb9\x89`\xf18\xdb\x02\xc77\x97'  # noqa: E501
PAY_ABI: Final = '{"anonymous":false,"inputs":[{"indexed":true,"internalType":"uint256","name":"fundingCycleConfiguration","type":"uint256"},{"indexed":true,"internalType":"uint256","name":"fundingCycleNumber","type":"uint256"},{"indexed":true,"internalType":"uint256","name":"projectId","type":"uint256"},{"indexed":false,"internalType":"address","name":"payer","type":"address"},{"indexed":false,"internalType":"address","name":"beneficiary","type":"address"},{"indexed":false,"internalType":"uint256","name":"amount","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"beneficiaryTokenCount","type":"uint256"},{"indexed":false,"internalType":"string","name":"memo","type":"string"},{"indexed":false,"internalType":"bytes","name":"metadata","type":"bytes"},{"indexed":false,"internalType":"address","name":"caller","type":"address"}],"name":"Pay","type":"event"}'  # noqa: E501
METADATA_CONTENT_OF_ABI: Final[ABI] = [{'inputs': [{'name': '', 'type': 'uint256'}, {'name': '', 'type': 'uint256'}], 'name': 'metadataContentOf', 'outputs': [{'name': '', 'type': 'string'}], 'stateMutability': 'view', 'type': 'function'}]  # noqa: E501

TERMINAL_3_1_2: Final = string_to_evm_address('0x1d9619E10086FdC1065B114298384aAe3F680CC0')
JUICEBOX_PROJECTS: Final = string_to_evm_address('0xD8B4359143eda5B2d763E127Ed27c77addBc47d3')

CHARITY_PROJECTS_IDS: Final = {
    618,  # Free Alexey & Roman
    615,  # CodeMinds Academy
}
JUICEBOX_IPFS_GATEWAY: Final = 'https://jbm.infura-ipfs.io/ipfs/'
CHARITY_TAG: Final = 'charity'
