from typing import List, NamedTuple, Optional, Tuple

from rotkehlchen.chain.bitcoin import have_bitcoin_transactions
from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.fval import FVal
from rotkehlchen.typing import BTCAddress

XPUB_ADDRESS_STEP = 10


class XpubData(NamedTuple):
    xpub: HDKey
    derivation_path: Optional[str] = None
    label: Optional[str] = None
    tags: Optional[List[str]] = None

    def serialize_derivation_path(self) -> str:
        """
        In Rotki we store non-existing path as None but in sql it must be ''
        https://stackoverflow.com/questions/43827629/why-does-sqlite-insert-duplicate-composite-primary-keys
        """
        return '' if self.derivation_path is None else self.derivation_path


def deserialize_derivation_path(path: str) -> Optional[str]:
    """
    In Rotki we store non-existing path as None but in sql it must be ''
    https://stackoverflow.com/questions/43827629/why-does-sqlite-insert-duplicate-composite-primary-keys
    """
    return None if path == '' else path


class XpubDerivedAddressData(NamedTuple):
    account_index: int
    derived_index: int
    address: BTCAddress
    balance: FVal


def _derive_addresses_loop(
        account_index: int,
        start_index: int,
        root: HDKey,
) -> List[XpubDerivedAddressData]:
    step_index = start_index
    addresses: List[XpubDerivedAddressData] = []
    should_continue = True
    while should_continue:
        print(f'Account:{account_index} step_index:{step_index}')
        batch_addresses: List[Tuple[int, BTCAddress]] = []
        for idx in range(step_index, step_index + XPUB_ADDRESS_STEP):
            child = root.derive_child(idx)
            batch_addresses.append((idx, child.address()))

        have_tx_mapping = have_bitcoin_transactions([x[1] for x in batch_addresses])
        for idx, address in batch_addresses:
            have_tx, balance = have_tx_mapping[address]
            if have_tx:
                addresses.append(XpubDerivedAddressData(
                    account_index=account_index,
                    derived_index=idx,
                    address=address,
                    balance=balance,
                ))
            else:
                should_continue = False

        # do one more pass and add any addresses with no transactions before the max index
        # this is so we can start new address generation from the max index later
        if len(addresses) != 0:
            max_index = max(x[0] for x in addresses)
            for idx, address in batch_addresses[:max_index]:
                have_tx, balance = have_tx_mapping[address]
                if not have_tx:
                    addresses.append(XpubDerivedAddressData(
                        account_index=account_index,
                        derived_index=idx,
                        address=address,
                        balance=balance,
                    ))

        step_index += XPUB_ADDRESS_STEP

    return addresses


def derive_addresses_from_xpub_data(
        xpub_data: XpubData,
        start_receiving_index: int,
        start_change_index: int,
) -> List[XpubDerivedAddressData]:
    """Derive all addresses from the xpub that have had transactions. Also includes
    any addresses until the biggest index derived addresses that have had no transactions.
    This is to make it easier to later derive and check more addresses"""
    if xpub_data.derivation_path is not None:
        account_xpub = xpub_data.xpub.derive_path(xpub_data.derivation_path)
    else:
        account_xpub = xpub_data.xpub

    addresses = []
    receiving_xpub = account_xpub.derive_child(0)
    addresses.extend(
        _derive_addresses_loop(
            account_index=0,
            start_index=start_receiving_index,
            root=receiving_xpub,
        ),
    )
    change_xpub = account_xpub.derive_child(1)
    addresses.extend(
        _derive_addresses_loop(
            account_index=1,
            start_index=start_change_index,
            root=change_xpub,
        ),
    )
    return addresses
