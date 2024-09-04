from typing import Final

from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_GMX: Final = 'gmx'

GMX_VAULT_ADDRESS: Final = string_to_evm_address('0x489ee077994B6658eAfA855C308275EAd8097C4A')
GMX_ROUTER_ADDRESS: Final = string_to_evm_address('0xaBBc5F99639c9B6bCb58544ddf04EFA6802F4064')
GMX_POSITION_ROUTER: Final = string_to_evm_address('0xb87a436B93fFE9D75c5cFA7bAcFff96430b09868')
GMX_REWARD_ROUTER: Final = string_to_evm_address('0x159854e14A862Df9E39E1D128b8e5F70B4A3cE9B')
GMX_READER: Final = string_to_evm_address('0x22199a49A999c351eF7927602CFB187ec3cae489')
GMX_STAKING_REWARD: Final = string_to_evm_address('0x908C4D94D34924765f1eDc22A1DD098397c59dD4')
SWAP_TOPIC: Final = b'\xcd8)\xa3\x81=\xc3\xcd\xd1\x88\xfd=\x01\xdc\xf3&\x8c\x16\xbe/\xdd-\xd2\x1d\x06eA\x88\x16\xe4`b'  # noqa: E501
CREATE_INCREASE_TOPIC: Final = b'Re\xbcIR\xda@&3\xb3\xfc5\xf6z\xb4$T\x93\xa0\xab\x94\xdd\x8a\xb1#f|\x8dE\xa4H\\'  # noqa: E501
EXECUTE_DECREASE_TOPIC: Final = b'!C\\[a\x8dw\xff6W\x14\x0c\xd31\x8e,\xff\xae\xbc^\x0e\x1bs\x18\xf5j\x9b\xa4\x04L>\xd2'  # noqa: E501
STAKE_GMX: Final = b'\xad\x07#\x80j\xa1\xe5\xa8\xfb\x82o\xc9\xf0\xc5\xb5\x89\xe5\x85\xa6\xb6\r\xc7h\xa1\xb2\x06\x91\xc9Pb\xd2\xd6'  # noqa: E501

EXECUTE_DECREASE_ABI: Final = '{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"account","type":"address"},{"indexed":false,"internalType":"address[]","name":"path","type":"address[]"},{"indexed":false,"internalType":"address","name":"indexToken","type":"address"},{"indexed":false,"internalType":"uint256","name":"collateralDelta","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"sizeDelta","type":"uint256"},{"indexed":false,"internalType":"bool","name":"isLong","type":"bool"},{"indexed":false,"internalType":"address","name":"receiver","type":"address"},{"indexed":false,"internalType":"uint256","name":"acceptablePrice","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"minOut","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"executionFee","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"blockGap","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"timeGap","type":"uint256"}],"name":"ExecuteDecreasePosition","type":"event"}'  # noqa: E501
EXECUTE_INCREASE_ABI: Final = '{"anonymous":false,"inputs":[{"indexed":true,"internalType":"address","name":"account","type":"address"},{"indexed":false,"internalType":"address[]","name":"path","type":"address[]"},{"indexed":false,"internalType":"address","name":"indexToken","type":"address"},{"indexed":false,"internalType":"uint256","name":"amountIn","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"minOut","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"sizeDelta","type":"uint256"},{"indexed":false,"internalType":"bool","name":"isLong","type":"bool"},{"indexed":false,"internalType":"uint256","name":"acceptablePrice","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"executionFee","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"index","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"queueIndex","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"blockNumber","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"blockTime","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"gasPrice","type":"uint256"}],"name":"CreateIncreasePosition","type":"event"}'  # noqa: E501
GMX_USD_DECIMALS: Final = 30
