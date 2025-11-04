from typing import Final

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.hop.structures import HopBridgeEventData
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_WETH_POLYGON, A_WPOL

BRIDGES: Final = {
    string_to_evm_address('0xb98454270065A31D71Bf635F6F7Ee6A518dFb849'): HopBridgeEventData(
        identifier=A_WETH_POLYGON.identifier,
        amm_wrapper=string_to_evm_address('0xc315239cFb05F1E130E7E28E603CEa4C014c57f0'),
        hop_identifier='eip155:137/erc20:0x1fDeAF938267ca43388eD1FdB879eaF91e920c7A',
        saddle_swap=string_to_evm_address('0x266e2dc3C4c59E42AA07afeE5B09E964cFFe6778'),
    ), string_to_evm_address('0x25D8039bB044dC227f741a9e381CA4cEAE2E6aE8'): HopBridgeEventData(
        identifier='eip155:137/erc20:0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174',
        amm_wrapper=string_to_evm_address('0x76b22b8C1079A44F1211D867D68b1eda76a635A7'),
        hop_identifier='eip155:137/erc20:0x9ec9551d4A1a1593b0ee8124D98590CC71b3B09D',
        saddle_swap=string_to_evm_address('0x5C32143C8B198F392d01f8446b754c181224ac26'),
    ), string_to_evm_address('0x6c9a1ACF73bd85463A46B0AFc076FBdf602b690B'): HopBridgeEventData(
        identifier='eip155:137/erc20:0xc2132D05D31c914a87C6611C10748AEb04B58e8F',
        amm_wrapper=string_to_evm_address('0x8741Ba6225A6BF91f9D73531A98A89807857a2B3'),
        hop_identifier='eip155:137/erc20:0x9F93ACA246F457916E49Ec923B8ed099e313f763',
        saddle_swap=string_to_evm_address('0xB2f7d27B21a69a033f85C42d5EB079043BAadC81'),
    ), string_to_evm_address('0x553bC791D746767166fA3888432038193cEED5E2'): HopBridgeEventData(
        identifier=A_WPOL.identifier,
        amm_wrapper=string_to_evm_address('0x884d1Aa15F9957E1aEAA86a82a72e49Bc2bfCbe3'),
        hop_identifier='eip155:137/erc20:0x712F0cf37Bdb8299D0666727F73a5cAbA7c1c24c',
        saddle_swap=string_to_evm_address('0x3d4Cc8A61c7528Fd86C55cfe061a78dCBA48EDd1'),
    ), string_to_evm_address('0xEcf268Be00308980B5b3fcd0975D47C4C8e1382a'): HopBridgeEventData(
        identifier='eip155:137/erc20:0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063',
        amm_wrapper=string_to_evm_address('0x28529fec439cfF6d7D1D5917e956dEE62Cd3BE5c'),
        hop_identifier='eip155:137/erc20:0xb8901acB165ed027E32754E0FFe830802919727f',
        saddle_swap=string_to_evm_address('0x25FB92E505F752F730cAD0Bd4fa17ecE4A384266'),
    ), string_to_evm_address('0x58c61AeE5eD3D748a1467085ED2650B697A66234'): HopBridgeEventData(
        identifier='eip155:137/erc20:0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC',
        amm_wrapper=ZERO_ADDRESS,
        hop_identifier='eip155:137/erc20:0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC',
    ),
}

REWARD_CONTRACTS: Final = {
    string_to_evm_address('0x2C2Ab81Cf235e86374468b387e241DF22459A265'),  # WMATIC (USDC.e)
    string_to_evm_address('0x7811737716942967Ae6567B26a5051cC72af550E'),  # HOP (USDC.e)
    string_to_evm_address('0x07932e9A5AB8800922B2688FB1FA0DAAd8341772'),  # WMATIC (USDT)
    string_to_evm_address('0x297E5079DF8173Ae1696899d3eACD708f0aF82Ce'),  # HOP (USDT)
    string_to_evm_address('0x4Aeb0B5B1F3e74314A7Fa934dB090af603E8289b'),  # WMATIC (DAI)
    string_to_evm_address('0xd6dC6F69f81537Fe9DEcc18152b7005B45Dc2eE7'),  # HOP (DAI)
    string_to_evm_address('0x7bCeDA1Db99D64F25eFA279BB11CE48E15Fda427'),  # WMATIC (ETH)
    string_to_evm_address('0xAA7b3a4A084e6461D486E53a03CF45004F0963b7'),  # HOP (ETH)
    string_to_evm_address('0x7dEEbCaD1416110022F444B03aEb1D20eB4Ea53f'),  # WMATIC (MATIC)
}
