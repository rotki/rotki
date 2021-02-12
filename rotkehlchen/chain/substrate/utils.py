from substrateinterface import Keypair
from substrateinterface.utils.ss58 import ss58_decode

from .typing import (
    KusamaAddress,
    KusamaNodeName,
    SubstrateAddress,
    SubstrateChain,
    SubstratePublicKey,
)

KUSAMA_NODES_TO_CONNECT_AT_START = (
    KusamaNodeName.OWN,
    KusamaNodeName.PARITY,
)
KUSAMA_NODE_CONNECTION_TIMEOUT = 10


def is_valid_kusama_address(value: str) -> bool:
    return is_valid_substrate_address(
        chain=SubstrateChain.KUSAMA,
        value=value,
    )


def is_valid_substrate_address(
        chain: SubstrateChain,
        value: str,
) -> bool:
    """Validates a ss58 encoded substrate address for the given chain.

    TODO: this function relies on py-scale-codec `ss58_decode()` for validating
    that a str is a valid substrate address for the given chain. The recent
    changes introduced on the py-scale-codec library have altered the behavior
    of this function by validating positively any str starting with `0x`. An
    issue has been opened regarding this matter (link below). Once py-scale-codec
    implements its own address validation method this function may be no longer
    needed. Issue:
    https://github.com/polkascan/py-scale-codec/issues/27

    Polkascan ss58 utils documentation:
    https://github.com/polkascan/py-substrate-interface/blob/master/substrateinterface/utils/ss58.py  # noqa: E501

    External Address Format (SS58) documentation:
    https://github.com/paritytech/substrate/wiki/External-Address-Format-(SS58)
    """
    if value.startswith('0x'):
        # TODO: temporary patch for py-scale-codec/issue/27
        return False

    if chain == SubstrateChain.KUSAMA:
        valid_ss58_format = 2
    else:
        raise AssertionError(f'Unexpected chain: {chain}')

    try:
        ss58_decode(
            address=value,
            valid_ss58_format=valid_ss58_format,
        )
    except ValueError:
        return False

    return True


def get_kusama_address_from_public_key(public_key: SubstratePublicKey) -> KusamaAddress:
    """Return a valid Kusama address given a Substrate public key.

    Public key: 32 len str, leading '0x' is optional.

    May raise:
    - AttributeError: if public key is not a string.
    - TypeError: if ss58_format is not an int.
    - ValueError: if public key is not 32 bytes long or the ss58_format is not
    a valid int.
    """
    return get_substrate_address_from_public_key(
        chain=SubstrateChain.KUSAMA,
        public_key=public_key,
    )


def get_substrate_address_from_public_key(
        chain: SubstrateChain,
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
    if chain == SubstrateChain.KUSAMA:
        ss58_format = 2
    else:
        raise AssertionError(f'Unexpected chain: {chain}')

    keypair = Keypair(
        public_key=public_key,
        ss58_format=ss58_format,
    )
    return SubstrateAddress(keypair.ss58_address)
