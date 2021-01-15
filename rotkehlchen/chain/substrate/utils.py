from substrateinterface.utils.ss58 import ss58_decode

from .typing import KusamaNodeName, SubstrateChain

KUSAMA_NODES_TO_CONNECT_AT_START = (
    KusamaNodeName.OWN,
    KusamaNodeName.PARITY,
)
KUSAMA_NODE_CONNECTION_TIMEOUT = 5


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

    Polkascan ss58 utils documentation:
    https://github.com/polkascan/py-substrate-interface/blob/master/substrateinterface/utils/ss58.py  # noqa: E501

    External Address Format (SS58) documentation:
    https://github.com/paritytech/substrate/wiki/External-Address-Format-(SS58)
    """
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
