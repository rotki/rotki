from typing import Final

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

AIRDROP_CLAIM: Final = b'\x04g R\xdc\xb6\xb5\xb1\x9a\x9c\xc2\xec\x1b\x8fD\x7f\x1f^G\xb5\xe2L\xfa^O\xfbd\rc\xca+\xe7'  # noqa: E501


# TODO: Probably this mapping needs to go somewhere else as part of
# https://github.com/rotki/rotki/issues/1420
# Also we should have similar logic per evm chain. This is not a good solution.
# Map of known addresses to some names. Names sourced by various sources
# including but not limited to etherscan's labels
KRAKEN_ADDRESSES: Final = frozenset({
    string_to_evm_address('0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2'),  # Kraken
    string_to_evm_address('0xAe2D4617c862309A3d75A0fFB358c7a5009c673F'),  # Kraken 10
    string_to_evm_address('0x098cbdd8eb01b19D37539644821772e9bdE12D55'),  # Kraken 20
    string_to_evm_address('0x43984D578803891dfa9706bDEee6078D80cFC79E'),  # Kraken 11
    string_to_evm_address('0x66c57bF505A85A74609D2C83E94Aabb26d691E1F'),  # Kraken 12
    string_to_evm_address('0xDA9dfA130Df4dE4673b89022EE50ff26f6EA73Cf'),  # Kraken 13
    string_to_evm_address('0x0A869d79a7052C7f1b55a8EbAbbEa3420F0D1E13'),  # Kraken 2
    string_to_evm_address('0xE853c56864A2ebe4576a807D26Fdc4A0adA51919'),  # Kraken 3
    string_to_evm_address('0x267be1C1D684F78cb4F6a176C4911b741E4Ffdc0'),  # Kraken 4
    string_to_evm_address('0xFa52274DD61E1643d2205169732f29114BC240b3'),  # Kraken 5
    string_to_evm_address('0x53d284357ec70cE289D6D64134DfAc8E511c8a3D'),  # Kraken 6
    string_to_evm_address('0x89e51fA8CA5D66cd220bAed62ED01e8951aa7c40'),  # Kraken 7
    string_to_evm_address('0xc6bed363b30DF7F35b601a5547fE56cd31Ec63DA'),  # Kraken 8
    string_to_evm_address('0x29728D0efd284D85187362fAA2d4d76C2CfC2612'),  # Kraken 9
    string_to_evm_address('0x26a78D5b6d7a7acEEDD1e6eE3229b372A624d8b7'),  # Kraken 57
    string_to_evm_address('0x94dBF04E273d87e6D9Bed68c616F43Bf86560C74'),  # Kraken 75
    string_to_evm_address('0x16B2b042f15564Bb8585259f535907F375Bdc415'),  # Kraken 33
    string_to_evm_address('0x10593a64B7b7BB0Ea29B8c01F1619ca8fF294b2F'),  # Kraken 25
    string_to_evm_address('0x0E33Be39B13c576ff48E14392fBf96b02F40Cd34'),  # Kraken 52
    string_to_evm_address('0x0D0452f487D1EDc869d1488ae984590ca2900D2F'),  # Kraken 16
    string_to_evm_address('0x52F5F2adD61c835ff10550402A46621EBd1071D5'),  # Kraken 49
    string_to_evm_address('0x0eF6AEB825dc4c9983d551F8aFEfaAE9d79165C6'),  # Kraken 70
    string_to_evm_address('0x53aB4a93B31F480d17D3440a6329bDa86869458A'),  # Kraken 53
    string_to_evm_address('0x491f5512751F5dB45c5415049D423aFfAaE70392'),  # Kraken 22
    string_to_evm_address('0x012480c08d20a14CF3Cb495e942a94dd926DCc8f'),  # Kraken 55
    string_to_evm_address('0x5203AeaaeE721195707b01e613B6c3259b3a5CF6'),  # Kraken 31
    string_to_evm_address('0x3FF7215004Fea03c2C745E0476e3f412050e04D1'),  # Kraken 69
    string_to_evm_address('0x16b34756653f88a89005E96C0622832D8fB6b0B5'),  # Kraken 65
    string_to_evm_address('0x4442c3E6B5f22B8b4dc3c9329be6c850C5779E85'),  # Kraken 59
    string_to_evm_address('0x34036F30371847C9fd8036B7eA5AF1b3126306dc'),  # Kraken 23
})

UPHOLD_ADDRESS: Final = string_to_evm_address('0x340d693ED55d7bA167D184ea76Ea2Fd092a35BDc')
POLONIEX_ADDRESS: Final = string_to_evm_address('0x32Be343B94f860124dC4fEe278FDCBD38C102D88')

CPT_GNOSIS_CHAIN: Final = 'gnosis-chain'
GNOSIS_CPT_DETAILS: Final = CounterpartyDetails(
    identifier=CPT_GNOSIS_CHAIN,
    label='Gnosis Chain',
    image='gnosis.svg',
)
