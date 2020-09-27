from typing import List, NamedTuple, Optional, Tuple

from rotkehlchen.chain.bitcoin import have_bitcoin_transactions
from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.typing import BTCAddress

XPUB_ADDRESS_STEP = 20


class XpubData(NamedTuple):
    xpub: HDKey
    derivation_path: str
    label: Optional[str] = None
    tags: Optional[List[str]] = None


def derive_addresses_from_xpub_data(
        xpub_data: XpubData,
        start_index: int,
) -> List[Tuple[int, BTCAddress]]:
    step_index = start_index
    root = xpub_data.xpub.derive_path(xpub_data.derivation_path)

    addresses: List[Tuple[int, BTCAddress]] = []
    should_continue = True
    while should_continue:
        batch_addresses: List[Tuple[int, BTCAddress]] = []
        for idx in range(step_index, step_index + XPUB_ADDRESS_STEP):
            child = root.derive_child(idx)
            batch_addresses.append((idx, child.address()))

        have_tx_mapping = have_bitcoin_transactions([x[1] for x in batch_addresses])
        for idx, address in batch_addresses:
            if have_tx_mapping[address]:
                addresses.append((idx, address))
            else:
                should_continue = False

        step_index += XPUB_ADDRESS_STEP

    return addresses
