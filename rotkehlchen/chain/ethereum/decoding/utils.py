from typing import Optional

from rotkehlchen.chain.ethereum.constants import CPT_KRAKEN
from rotkehlchen.types import ChecksumEvmAddress

from .constants import ETHADDRESS_TO_KNOWN_NAME


def address_is_exchange(address: ChecksumEvmAddress) -> Optional[str]:
    name = ETHADDRESS_TO_KNOWN_NAME.get(address)
    if name and 'Kraken' in name:
        return CPT_KRAKEN
    return None
