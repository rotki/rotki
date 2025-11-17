from typing import get_args

from substrateinterface import Keypair
from substrateinterface.utils.ss58 import is_valid_ss58_address

from rotkehlchen.types import SUPPORTED_SUBSTRATE_CHAINS_TYPE, SupportedBlockchain

from .types import KusamaNodeName, PolkadotNodeName, SubstrateAddress, SubstratePublicKey

KUSAMA_NODES_TO_CONNECT_AT_START = (
    KusamaNodeName.OWN,
    KusamaNodeName.DWELLIR,
    KusamaNodeName.STAKEWORLD,
    KusamaNodeName.ONFINALITY,
)

POLKADOT_NODES_TO_CONNECT_AT_START = (
    PolkadotNodeName.OWN,
    PolkadotNodeName.DWELLIR,
    PolkadotNodeName.STAKEWORLD,
    PolkadotNodeName.ONFINALITY,
)

# This is a timeout in gevent, so should be generous as it's not only for
# the single connection, but for all other greenlets that can be context
# switched in the meantime
SUBSTRATE_NODE_CONNECTION_TIMEOUT = 60


def is_valid_substrate_address(chain: SUPPORTED_SUBSTRATE_CHAINS_TYPE, value: str) -> bool:
    return is_valid_ss58_address(
        value=value,
        valid_ss58_format=2 if chain == SupportedBlockchain.KUSAMA else 0,
    )


def get_substrate_address_from_public_key(
        chain: SUPPORTED_SUBSTRATE_CHAINS_TYPE,
        public_key: SubstratePublicKey,
) -> SubstrateAddress:
    """Return a valid address for the given Substrate chain and public key.

    Public key: 32 len str, leading '0x' is optional.

    May raise:
    - AttributeError: if public key is not a string.
    - TypeError: if ss58_format is not an int.
    - ValueError: if public key is not 32 bytes long or the ss58_format is not
    a valid int.
    """
    assert chain in get_args(SUPPORTED_SUBSTRATE_CHAINS_TYPE)
    if chain == SupportedBlockchain.KUSAMA:
        ss58_format = 2
    else:  # polkadot
        ss58_format = 0

    keypair = Keypair(
        public_key=public_key,
        ss58_format=ss58_format,
    )
    return SubstrateAddress(keypair.ss58_address)
