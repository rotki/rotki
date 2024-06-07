from typing import TYPE_CHECKING, Final

from rotkehlchen.chain.evm.decoding.types import CounterpartyDetails
from rotkehlchen.chain.evm.decoding.uniswap_v2_like.decoder import UniswapV2LikeDecoder
from rotkehlchen.chain.evm.types import string_to_evm_address
from rotkehlchen.constants.assets import A_WETH_SCROLL
from rotkehlchen.types import ChecksumEvmAddress

if TYPE_CHECKING:
    from rotkehlchen.chain.evm.decoding.base import BaseDecoderTools
    from rotkehlchen.chain.scroll.node_inquirer import ScrollInquirer
    from rotkehlchen.user_messages import MessagesAggregator


# https://syncswap.gitbook.io/api-documentation/resources/smart-contract#scroll-alpha-testnet
SYNCSWAP_ROUTER_ADDRESS: Final = string_to_evm_address('0x80e38291e06339d10AAB483C65695D004dBD5C69')  # noqa: E501
SYNCSWAP_VAULT_ADDRESS: Final = string_to_evm_address('0x7160570BB153Edd0Ea1775EC2b2Ac9b65F1aB61B')
CPT_SYNCSWAP: Final = 'syncswap'
SYNCSWAP_LABEL: Final = 'Syncswap'
SYNCSWAP_ICON: Final = 'syncswap.svg'
SYNCSWAP_CLASSIC_POOL_FACTORY_ADDRESS: Final = string_to_evm_address('0x37BAc764494c8db4e54BDE72f6965beA9fa0AC2d')  # noqa: E501
SYNCSWAP_STABLE_POOL_FACTORY_ADDRESS: Final = string_to_evm_address('0xE4CF807E351b56720B17A59094179e7Ed9dD3727')  # noqa: E501
# The init code hash is looked up using the RPC method debug_traceTransaction() from the pool initialization transaction  # noqa: E501
# The pool_bytecode is the input of the CREATE2 call, then we pass it to Web3.keccak(hexstring_to_bytes(pool_bytecode))  # noqa: E501
SYNCSWAP_INIT_CODE_HASH: Final = '0x4f735b697ebe21f2cde0de70538125c07a001ddb644057e31d233b4e8dce5b14'  # noqa: E501
SYNCSWAP_STABLE_INIT_CODE_HASH: Final = '0x7707e822b378208b3b349ea0f4cec2eae444b98027043eab01a44003f57bd2f2'  # noqa: E501


class SyncswapDecoder(UniswapV2LikeDecoder):

    def __init__(
            self,
            evm_inquirer: 'ScrollInquirer',
            base_tools: 'BaseDecoderTools',
            msg_aggregator: 'MessagesAggregator',
    ) -> None:
        super().__init__(
            evm_inquirer=evm_inquirer,
            base_tools=base_tools,
            msg_aggregator=msg_aggregator,
            counterparty_addresses=[SYNCSWAP_ROUTER_ADDRESS, SYNCSWAP_VAULT_ADDRESS],
            pool_address_setup={
                SYNCSWAP_CLASSIC_POOL_FACTORY_ADDRESS: SYNCSWAP_INIT_CODE_HASH,
                SYNCSWAP_STABLE_POOL_FACTORY_ADDRESS: SYNCSWAP_STABLE_INIT_CODE_HASH,
            },
        )
        self.weth_asset = A_WETH_SCROLL.resolve_to_evm_token()

    # -- DecoderInterface methods

    @staticmethod
    def counterparties() -> tuple[CounterpartyDetails, ...]:
        return (CounterpartyDetails(
            identifier=CPT_SYNCSWAP,
            label=SYNCSWAP_LABEL,
            image=SYNCSWAP_ICON,
        ),)

    def addresses_to_counterparties(self) -> dict[ChecksumEvmAddress, str]:
        return dict.fromkeys([SYNCSWAP_ROUTER_ADDRESS, SYNCSWAP_VAULT_ADDRESS], CPT_SYNCSWAP)
