from rotkehlchen.chain.evm.types import string_to_evm_address

GTC_CLAIM = b'\x04g R\xdc\xb6\xb5\xb1\x9a\x9c\xc2\xec\x1b\x8fD\x7f\x1f^G\xb5\xe2L\xfa^O\xfbd\rc\xca+\xe7'  # noqa: E501
ONEINCH_CLAIM = b'N\xc9\x0e\x96U\x19\xd9&\x81&tg\xf7u\xad\xa5\xbd!J\xa9,\r\xc9=\x90\xa5\xe8\x80\xce\x9e\xd0&'  # noqa: E501
GNOSIS_CHAIN_BRIDGE_RECEIVE = b'\x9a\xfdG\x90~%\x02\x8c\xda\xca\x89\xd1\x93Q\x8c0+\xbb\x12\x86\x17\xd5\xa9\x92\xc5\xab\xd4X\x15Re\x93'  # noqa: E501
GOVERNORALPHA_PROPOSE = b"}\x84\xa6&:\xe0\xd9\x8d3)\xbd{F\xbbN\x8do\x98\xcd5\xa7\xad\xb4\\'L\x8b\x7f\xd5\xeb\xd5\xe0"  # noqa: E501
GOVERNORALPHA_PROPOSE_ABI = '{"anonymous":false,"inputs":[{"indexed":false,"internalType":"uint256","name":"id","type":"uint256"},{"indexed":false,"internalType":"address","name":"proposer","type":"address"},{"indexed":false,"internalType":"address[]","name":"targets","type":"address[]"},{"indexed":false,"internalType":"uint256[]","name":"values","type":"uint256[]"},{"indexed":false,"internalType":"string[]","name":"signatures","type":"string[]"},{"indexed":false,"internalType":"bytes[]","name":"calldatas","type":"bytes[]"},{"indexed":false,"internalType":"uint256","name":"startBlock","type":"uint256"},{"indexed":false,"internalType":"uint256","name":"endBlock","type":"uint256"},{"indexed":false,"internalType":"string","name":"description","type":"string"}],"name":"ProposalCreated","type":"event"}'  # noqa: E501


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
