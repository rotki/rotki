from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.types import string_to_evm_address

GTC_CLAIM = b'\x04g R\xdc\xb6\xb5\xb1\x9a\x9c\xc2\xec\x1b\x8fD\x7f\x1f^G\xb5\xe2L\xfa^O\xfbd\rc\xca+\xe7'  # noqa: E501


# TODO: Probably this mapping needs to go somewhere else as part of
# https://github.com/rotki/rotki/issues/1420
# Map of known addresses to some names. Names sourced by various sources
# including but not limited to etherscan's labels
ETHADDRESS_TO_KNOWN_NAME = {
    string_to_evm_address('0x2910543Af39abA0Cd09dBb2D50200b3E800A63D2'): 'Kraken',
    string_to_evm_address('0xAe2D4617c862309A3d75A0fFB358c7a5009c673F'): 'Kraken 10',
    string_to_evm_address('0x43984D578803891dfa9706bDEee6078D80cFC79E'): 'Kraken 11',
    string_to_evm_address('0x66c57bF505A85A74609D2C83E94Aabb26d691E1F'): 'Kraken 12',
    string_to_evm_address('0xDA9dfA130Df4dE4673b89022EE50ff26f6EA73Cf'): 'Kraken 13',
    string_to_evm_address('0x0A869d79a7052C7f1b55a8EbAbbEa3420F0D1E13'): 'Kraken 2',
    string_to_evm_address('0xE853c56864A2ebe4576a807D26Fdc4A0adA51919'): 'Kraken 3',
    string_to_evm_address('0x267be1C1D684F78cb4F6a176C4911b741E4Ffdc0'): 'Kraken 4',
    string_to_evm_address('0xFa52274DD61E1643d2205169732f29114BC240b3'): 'Kraken 5',
    string_to_evm_address('0x53d284357ec70cE289D6D64134DfAc8E511c8a3D'): 'Kraken 6',
    string_to_evm_address('0x89e51fA8CA5D66cd220bAed62ED01e8951aa7c40'): 'Kraken 7',
    string_to_evm_address('0xc6bed363b30DF7F35b601a5547fE56cd31Ec63DA'): 'Kraken 8',
    string_to_evm_address('0x29728D0efd284D85187362fAA2d4d76C2CfC2612'): 'Kraken 9',

    string_to_evm_address('0x340d693ED55d7bA167D184ea76Ea2Fd092a35BDc'): 'Uphold.com',
}

CPT_GNOSIS_CHAIN = 'gnosis-chain'
GNOSIS_CPT_DETAILS = CounterpartyDetails(
    identifier=CPT_GNOSIS_CHAIN,
    label='Gnosis Chain',
    image='gnosis.svg',
)
