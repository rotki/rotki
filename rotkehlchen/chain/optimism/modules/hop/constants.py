from typing import Final

from rotkehlchen.chain.evm.constants import ZERO_ADDRESS
from rotkehlchen.chain.evm.decoding.hop.structures import HopBridgeEventData
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_ETH

BRIDGES: Final = {
    string_to_evm_address('0x83f6244Bd87662118d96D9a6D44f09dffF14b30E'): HopBridgeEventData(
        identifier=A_ETH.identifier,
        amm_wrapper=string_to_evm_address('0x86cA30bEF97fB651b8d866D45503684b90cb3312'),
        hop_identifier='eip155:10/erc20:0xE38faf9040c7F09958c638bBDB977083722c5156',
        saddle_swap=string_to_evm_address('0xaa30D6bba6285d0585722e2440Ff89E23EF68864'),
    ), string_to_evm_address('0xa81D244A1814468C734E5b4101F7b9c0c577a8fC'): HopBridgeEventData(
        identifier='eip155:10/erc20:0x7F5c764cBc14f9669B88837ca1490cCa17c31607',
        amm_wrapper=string_to_evm_address('0x2ad09850b0CA4c7c1B33f5AcD6cBAbCaB5d6e796'),
        hop_identifier='eip155:10/erc20:0x25D8039bB044dC227f741a9e381CA4cEAE2E6aE8',
        saddle_swap=string_to_evm_address('0x3c0FFAca566fCcfD9Cc95139FEF6CBA143795963'),
    ), string_to_evm_address('0x46ae9BaB8CEA96610807a275EBD36f8e916b5C61'): HopBridgeEventData(
        identifier='eip155:10/erc20:0x94b008aA00579c1307B0EF2c499aD98a8ce58e58',
        amm_wrapper=string_to_evm_address('0x7D269D3E0d61A05a0bA976b7DBF8805bF844AF3F'),
        hop_identifier='eip155:10/erc20:0x2057C8ECB70Afd7Bee667d76B4CD373A325b1a20',
        saddle_swap=string_to_evm_address('0xeC4B41Af04cF917b54AEb6Df58c0f8D78895b5Ef'),
    ), string_to_evm_address('0x7191061D5d4C60f598214cC6913502184BAddf18'): HopBridgeEventData(
        identifier='eip155:10/erc20:0xDA10009cBd5D07dd0CeCc66161FC93D7c9000da1',
        amm_wrapper=string_to_evm_address('0xb3C68a491608952Cb1257FC9909a537a0173b63B'),
        hop_identifier='eip155:10/erc20:0x56900d66D74Cb14E3c86895789901C9135c95b16',
        saddle_swap=string_to_evm_address('0xF181eD90D6CfaC84B8073FdEA6D34Aa744B41810'),
    ), string_to_evm_address('0x03D7f750777eC48d39D080b020D83Eb2CB4e3547'): HopBridgeEventData(
        identifier='eip155:10/erc20:0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC',
        amm_wrapper=ZERO_ADDRESS,
        hop_identifier='eip155:10/erc20:0xc5102fE9359FD9a28f877a67E36B0F050d81a3CC',
    ), string_to_evm_address('0x16284c7323c35F4960540583998C98B1CfC581a7'): HopBridgeEventData(
        identifier='eip155:10/erc20:0x8700dAec35aF8Ff88c16BdF0418774CB3D7599B4',
        amm_wrapper=string_to_evm_address('0xf11EBB94EC986EA891Aec29cfF151345C83b33Ec'),
        hop_identifier='eip155:10/erc20:0x13B7F51BD865410c3AcC4d56083C5B56aB38D203',
        saddle_swap=string_to_evm_address('0x1990BC6dfe2ef605Bfc08f5A23564dB75642Ad73'),
    ), string_to_evm_address('0x33Fe5bB8DA466dA55a8A32D6ADE2BB104E2C5201'): HopBridgeEventData(
        identifier='eip155:10/erc20:0x8c6f28f2F1A3C87F0f938b96d27520d9751ec8d9',
        amm_wrapper=string_to_evm_address('0x29Fba7d2A6C95DB162ee09C6250e912D6893DCa6'),
        hop_identifier='eip155:10/erc20:0x6F03052743CD99ce1b29265E377e320CD24Eb632',
        saddle_swap=string_to_evm_address('0x8d4063E82A4Db8CdAed46932E1c71e03CA69Bede'),
    ), string_to_evm_address('0xA0075E8cE43dcB9970cB7709b9526c1232cc39c2'): HopBridgeEventData(
        identifier='eip155:10/erc20:0x9Bcef72be871e61ED4fBbc7630889beE758eb81D',
        amm_wrapper=string_to_evm_address('0x19B2162CA4C2C6F08C6942bFB846ce5C396aCB75'),
        hop_identifier='eip155:10/erc20:0x755569159598f3702bdD7DFF6233A317C156d3Dd',
        saddle_swap=string_to_evm_address('0x9Dd8685463285aD5a94D2c128bda3c5e8a6173c8'),
    ),
}

REWARD_CONTRACTS: Final = {
    string_to_evm_address('0xf587B9309c603feEdf0445aF4D3B21300989e93a'),  # HOP (USDC.e)
    string_to_evm_address('0xAeB1b49921E0D2D96FcDBe0D486190B2907B3e0B'),  # HOP (USDT)
    string_to_evm_address('0x392B9780cFD362bD6951edFA9eBc31e68748b190'),  # HOP (DAI)
    string_to_evm_address('0x95d6A95BECfd98a7032Ed0c7d950ff6e0Fa8d697'),  # HOP (ETH)
    string_to_evm_address('0x25a5A48C35e75BD2EFf53D94f0BB60d5A00E36ea'),  # HOP (SNX)
    string_to_evm_address('0x09992Dd7B32f7b35D347DE9Bdaf1919a57d38E82'),  # OP (SNX)
    string_to_evm_address('0x2935008eE9943f859C4fbb863c5402fFC06f462E'),  # HOP (sUSD)
    string_to_evm_address('0x25FB92E505F752F730cAD0Bd4fa17ecE4A384266'),  # OP (sUSD)
    string_to_evm_address('0x266e2dc3C4c59E42AA07afeE5B09E964cFFe6778'),  # RPL (rETH)
    string_to_evm_address('0x45269F59aA76bB491D0Fc4c26F468D8E1EE26b73'),  # Merkle reewards (OP)
}
