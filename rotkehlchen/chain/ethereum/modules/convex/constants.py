from typing import Final

from rotkehlchen.chain.evm.constants import (
    REWARD_PAID_TOPIC,
    REWARD_PAID_TOPIC_V2,
    WITHDRAWN_TOPIC,
)
from rotkehlchen.chain.evm.decoding.constants import WITHDRAWN
from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

CPT_CONVEX: Final = 'convex'

CONVEX_CPT_DETAILS = CounterpartyDetails(
    identifier=CPT_CONVEX,
    label='Convex',
    image='convex.jpeg',
)

BOOSTER: Final = string_to_evm_address('0xF403C135812408BFbE8713b5A23a04b3D48AAE31')
CVX_LOCKER: Final = string_to_evm_address('0xD18140b4B819b895A3dba5442F959fA44994AF50')
CVX_LOCKER_V2: Final = string_to_evm_address('0x72a19342e8F1838460eBFCCEf09F6585e32db86E')
CVX_REWARDS: Final = string_to_evm_address('0xCF50b810E57Ac33B91dCF525C6ddd9881B139332')
CVXCRV_REWARDS: Final = string_to_evm_address('0x3Fe65692bfCD0e6CF84cB1E7d24108E434A7587e')

CVX_LOCK_WITHDRAWN: Final = b'/\xd8=^\x9f]$\x0b\xedG\xa9z$\xcf5N@G\xe2^\xdc-\xa2{\x01\xfd\x95\xe5\xe8\xa0\xc9\xa5'  # withdraw locked CVX  # noqa: E501

WITHDRAWAL_TOPICS = {
    WITHDRAWN,
    WITHDRAWN_TOPIC,
}

REWARD_TOPICS = {
    REWARD_PAID_TOPIC_V2,
    REWARD_PAID_TOPIC,
}

# example transaction: https://etherscan.io/tx/0xe03d27127fda879144ea4cc587470bd37040be9921ff6a90f48d4efd0cb4fe13#eventlog  # noqa: E501
# data about abras is taken from: https://github.com/convex-eth/platform/blob/eb87f1fddcf5efcc4294f564b58cca7ac4ccbc90/contracts/contracts.json  # noqa: E501
CONVEX_ABRAS_HEX = {  # using set since we only need to check if an address is "in" these pools
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xd9$\x94\xcb\x92\x1e\\\r:9\xea\x88\xd0\x14{\xbd\x82\xe5\x10\x08',
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00YX\xa8\xdb}\xfe\x0c\xc4\x93\x82 \x90i\xb0\x0fT\xe1y)\xc2',  # noqa: E501
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xb6^\xde\x13E!\xf0\xef\xd4\xe9C\xc85\xf4P\x13}\xc6\xe8>',
    b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00;\xa2\x07\xc2Z'\x85$\xe1\xcc\x7f\xaa\xea\x95\x07S\x04\x90r\xa4",
}


# Example transaction: https://etherscan.io/tx/0x5e62ce39159fcdf528905d044e5387c8f21a1eca015d08cebc652bfb9c183611  # noqa: E501
# Data taken from: https://etherscan.io/find-similar-contracts?a=0x7091dbb7fcba54569ef1387ac89eb2a5c9f6d2ea  # noqa: E501
# Convex might use virtual rewards pool as well as regular rewards, so we need to handle it.
CONVEX_VIRTUAL_REWARDS = [
    string_to_evm_address('0x7091dbb7fcbA54569eF1387Ac89Eb2a5C9F6d2EA'),
    string_to_evm_address('0x81fCe3E10D12Da6c7266a1A169c4C96813435263'),
    string_to_evm_address('0x7c41906Df8395AF4387fA79B85c845069f88eeC3'),
    string_to_evm_address('0x008aEa5036b819B4FEAEd10b2190FBb3954981E8'),
    string_to_evm_address('0x177252Ac74f1D77513971aA85AF7009C43EcdEe2'),
    string_to_evm_address('0xc095Cec98a9f8Ad6D2baA282A8e6bE246f98BD25'),
    string_to_evm_address('0x55d59b791f06dc519B176791c4E037E8Cf2f6361'),
    string_to_evm_address('0x93A5C724c4992FCBDA6b96F06fa15EB8B5c485b7'),
    string_to_evm_address('0x00469d388b06127221D6310843A43D079eb2bB18'),
    string_to_evm_address('0x20165075174b51a2f9Efbf7d6D8F3c72BBc63064'),
    string_to_evm_address('0x2Aa030dCB729CF94bc096Bd00d377aA719A09371'),
    string_to_evm_address('0xAE97D3766924526084dA88ba9B2bd7aF989Bf6fC'),
    string_to_evm_address('0x94C259DC4C6dF248B0b5D23C055CB7574A587d67'),
    string_to_evm_address('0xAF138B29205c2246B069Ed8f0b213b205FBc14E0'),
    string_to_evm_address('0xcDEC6714eB482f28f4889A0c122868450CDBF0b0'),
    string_to_evm_address('0x666F8eEE6FD6839853993977CC86a7A51425673C'),
    string_to_evm_address('0x681A790debE586A64eea055BF0983CD6629d8359'),
    string_to_evm_address('0xd731495bb78a4250bC094686788F3fF890dEe0f4'),
    string_to_evm_address('0x22a07a6bdA1CECbe2a671203e2114d8A170E5529'),
    string_to_evm_address('0x69a92f1656cd2e193797546cFe2EaF32EACcf6f7'),
    string_to_evm_address('0xbE4DEa8E5d1E53FAd661610E47501f858F25852D'),
    string_to_evm_address('0x771bc5c888d1B318D0c5b177e4F996d3D5fd3d18'),
    string_to_evm_address('0xE689DB5D753abc411ACB8a3fEf226C08ACDAE13f'),
    string_to_evm_address('0x91ad51F0897552ce77f76B44e9a86B4Ad2B28c25'),
    string_to_evm_address('0x21034ccc4f8D07d0cF8998Fdd4c45e426540dEc1'),
    string_to_evm_address('0x9D9EBCc8E7B4eF061C0F7Bab532d1710b874f789'),
    string_to_evm_address('0xE3A64E08EEbf38b19a3d9fec51d8cD5A8898Dd5e'),
    string_to_evm_address('0x8a3F52c2Eb02De2d8356a8286c96909352c62B10'),
    string_to_evm_address('0x00A4f5d12E3FAA909c53CDcC90968F735633e988'),
    string_to_evm_address('0x040A6Ae6314e190974ee4839f3c2FBf849EF54Eb'),
    string_to_evm_address('0xbA5eF047ce02cc0096DB3Bc8ED84aAD14291f8a0'),
    string_to_evm_address('0x1c86460640457466E2eC86916B4a91ED86CE0D1E'),
    string_to_evm_address('0x93649cd43635bC5F7Ad8fA2fa27CB9aE765Ec58A'),
    string_to_evm_address('0x5F91615268bE6b4aDD646b2560785B8F17dccBb4'),
    string_to_evm_address('0xCEc9a6efFf1daF52aF12beeBf87F81bda7b95c0b'),
    string_to_evm_address('0x27801399D60594BFeDe955D54c3e85B2f00179c5'),
    string_to_evm_address('0xb9E2e39c9C804a01f1FCB4e86F765774D511D535'),
    string_to_evm_address('0xAAf75a94394F6D06E01CcE62e2545CeFFBFA1E2D'),
    string_to_evm_address('0x880c2c5c4eA8cef892a90E3f714eB60144C08c30'),
    string_to_evm_address('0x08EDE581D9B9ae55FA7deCc4E4331D191BbBF9dB'),
    string_to_evm_address('0x8A05801c1512F6018e450b0F69e9Ca7b985fCea3'),
    string_to_evm_address('0x28a68d9c58086dAeB32d5c9297366cc91e50215D'),
    string_to_evm_address('0x74835A39Fd0e72E142d5E83D514e3eF6E7642220'),
    string_to_evm_address('0xE1eCBB4181378E2346EAC90Eb5606c01Aa08f052'),
    string_to_evm_address('0xb83EaADa3757432f7a894944C3ac154FbdBD8B46'),
    string_to_evm_address('0x834B9147Fd23bF131644aBC6e557Daf99C5cDa15'),
    string_to_evm_address('0xE2585F27bf5aaB7756f626D6444eD5Fc9154e606'),
    string_to_evm_address('0x28120D9D49dBAeb5E34D6B809b842684C482EF27'),
    string_to_evm_address('0x92dFd397b6d0B878126F5a5f6F446ae9Fc8A8356'),
    string_to_evm_address('0x19Ba12D57aD7B126dE898706AA6dBF7d6DC85FF8'),
    string_to_evm_address('0x640eBdA6C4f8D70A484C170106478ffb289a47DA'),
    string_to_evm_address('0xd48ad508E4e6d18bBBcA5042199e6b627dfCb331'),
    string_to_evm_address('0x498Dd51c2059D7e3008067841d1efE12D6c7F99c'),
    string_to_evm_address('0xe826994Cd8d4271A4b410B1b47e7DE5774Ba6E7A'),
    string_to_evm_address('0x3Ac6Ef1e811bACfa283ECC25ACAD1Cb858957bAb'),
    string_to_evm_address('0x5ab9Ea799904185939209c30Aa180f84AC58A63b'),
    string_to_evm_address('0x8E8E06F0555CA7A33C2c1a4e01875CEbF05Bda00'),
    string_to_evm_address('0x1BeCd991e1c5D0162718A215016d83E077a04cE9'),
    string_to_evm_address('0xCB200C57A6ef34a2e6bBfb5E02c3e44097F259Ee'),
]
