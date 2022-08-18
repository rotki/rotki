from typing import Literal, Union, overload

from substrateinterface import Keypair
from substrateinterface.utils.ss58 import is_valid_ss58_address

from .types import (
    KusamaAddress,
    KusamaNodeName,
    PolkadotAddress,
    PolkadotNodeName,
    SubstrateChain,
    SubstratePublicKey,
)

KUSAMA_NODES_TO_CONNECT_AT_START = (
    KusamaNodeName.OWN,
    KusamaNodeName.PARITY,
    KusamaNodeName.ELARA,
    KusamaNodeName.ONFINALITY,
)

POLKADOT_NODES_TO_CONNECT_AT_START = (
    PolkadotNodeName.OWN,
    PolkadotNodeName.PARITY,
    PolkadotNodeName.ELARA,
    PolkadotNodeName.ONFINALITY,
)

SUBSTRATE_NODE_CONNECTION_TIMEOUT = 10


def is_valid_kusama_address(value: str) -> bool:
    return is_valid_ss58_address(value=value, valid_ss58_format=2)


def is_valid_polkadot_address(value: str) -> bool:
    return is_valid_ss58_address(value=value, valid_ss58_format=0)


@overload
def get_substrate_address_from_public_key(
        chain: Literal[SubstrateChain.POLKADOT],
        public_key: SubstratePublicKey,
) -> PolkadotAddress:
    ...


@overload
def get_substrate_address_from_public_key(
        chain: Literal[SubstrateChain.KUSAMA],
        public_key: SubstratePublicKey,
) -> KusamaAddress:
    ...


def get_substrate_address_from_public_key(
        chain: SubstrateChain,
        public_key: SubstratePublicKey,
) -> Union[KusamaAddress, PolkadotAddress]:
    """Return a valid address for the given Substrate chain and public key.

    Public key: 32 len str, leading '0x' is optional.

    May raise:
    - AttributeError: if public key is not a string.
    - TypeError: if ss58_format is not an int.
    - ValueError: if public key is not 32 bytes long or the ss58_format is not
    a valid int.
    """
    if chain == SubstrateChain.KUSAMA:
        ss58_format = 2
    elif chain == SubstrateChain.POLKADOT:
        ss58_format = 0
    else:
        raise AssertionError(f'Unexpected chain: {chain}')

    keypair = Keypair(
        public_key=public_key,
        ss58_format=ss58_format,
    )
    if chain == SubstrateChain.KUSAMA:
        return KusamaAddress(keypair.ss58_address)
    # else can only be polkadot
    return PolkadotAddress(keypair.ss58_address)
