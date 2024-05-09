from typing import Final

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.hop.structures import HopBridgeEventData
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_WXDAI

BRIDGES: Final = {
    string_to_evm_address('0xD8926c12C0B2E5Cd40cFdA49eCaFf40252Af491B'): HopBridgeEventData(
        identifier='eip155:100/erc20:0x6A023CCd1ff6F2045C3309768eAd9E68F978f6e1',
        amm_wrapper=string_to_evm_address('0x03D7f750777eC48d39D080b020D83Eb2CB4e3547'),
        saddle_swap=string_to_evm_address('0x4014DC015641c08788F15bD6eB20dA4c47D936d8'),
    ), string_to_evm_address('0x25D8039bB044dC227f741a9e381CA4cEAE2E6aE8'): HopBridgeEventData(
        identifier='eip155:100/erc20:0xDDAfbb505ad214D7b80b1f830fcCc89B60fb7A83',
        amm_wrapper=string_to_evm_address('0x76b22b8C1079A44F1211D867D68b1eda76a635A7'),
        hop_identifier='eip155:100/erc20:0x9ec9551d4A1a1593b0ee8124D98590CC71b3B09D',
        saddle_swap=string_to_evm_address('0x5C32143C8B198F392d01f8446b754c181224ac26'),
    ), string_to_evm_address('0xFD5a186A7e8453Eb867A360526c5d987A00ACaC2'): HopBridgeEventData(
        identifier='eip155:100/erc20:0x4ECaBa5870353805a9F068101A40E0f32ed605C6',
        amm_wrapper=string_to_evm_address('0x49094a1B3463c4e2E82ca41b8e6A023bdd6E222f'),
        hop_identifier='eip155:100/erc20:0x91f8490eC27cbB1b2FaEdd29c2eC23011d7355FB',
        saddle_swap=string_to_evm_address('0x3Aa637D6853f1d9A9354FE4301Ab852A88b237e7'),
    ), string_to_evm_address('0x7ac71c29fEdF94BAc5A5C9aB76E1Dd12Ea885CCC'): HopBridgeEventData(
        identifier='eip155:100/erc20:0x7122d7661c4564b7C6Cd4878B06766489a6028A2',
        amm_wrapper=string_to_evm_address('0x86cA30bEF97fB651b8d866D45503684b90cb3312'),
        hop_identifier='eip155:100/erc20:0xE38faf9040c7F09958c638bBDB977083722c5156',
        saddle_swap=string_to_evm_address('0xaa30D6bba6285d0585722e2440Ff89E23EF68864'),
    ), string_to_evm_address('0x0460352b91D7CF42B0E1C1c30f06B602D9ef2238'): HopBridgeEventData(
        identifier=A_WXDAI.identifier,
        amm_wrapper=string_to_evm_address('0x6C928f435d1F3329bABb42d69CCF043e3900EcF1'),
        saddle_swap=string_to_evm_address('0x24afDcA4653042C6D08fb1A754b2535dAcF6Eb24'),
    ), string_to_evm_address('0x6F03052743CD99ce1b29265E377e320CD24Eb632'): HopBridgeEventData(
        identifier='eip155:100/erc20:0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC',
        amm_wrapper=ZERO_ADDRESS,
    ),
}
