from typing import TYPE_CHECKING, List, NamedTuple, Optional, Tuple

from rotkehlchen.chain.bitcoin import have_bitcoin_transactions
from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.db.utils import insert_tag_mappings
from rotkehlchen.fval import FVal
from rotkehlchen.typing import BlockchainAccountData, BTCAddress, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.chain.manager import BlockchainBalancesUpdate, ChainManager

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


class XpubManager():

    def __init__(self, chain_manager: 'ChainManager'):
        self.chain_manager = chain_manager
        self.db = chain_manager.database

    def add_bitcoin_xpub(self, xpub_data: XpubData) -> 'BlockchainBalancesUpdate':
        """
        May raise:
        - InputError: If the xpub already exists in the DB
        - TagConstraintError if any of the given account data contain unknown tags.
        - RemoteError if an external service such as blockcypher is queried and
          there is a problem with its query.
        """
        # First try to add the xpub, and if it already exists raise
        self.db.add_bitcoin_xpub(xpub_data)
        # Then add tags if not existing
        self.db.ensure_tags_exist(
            given_data=[xpub_data],
            action='adding',
            data_type='bitcoin xpub',
        )
        last_receiving_idx, last_change_idx = self.db.get_last_xpub_derived_indices(xpub_data)
        derived_addresses_data = derive_addresses_from_xpub_data(
            xpub_data=xpub_data,
            start_receiving_index=last_receiving_idx,
            start_change_index=last_change_idx,
        )
        known_btc_addresses = self.db.get_blockchain_accounts().btc

        new_addresses = []
        new_balances = []
        existing_address_data = []
        for entry in derived_addresses_data:
            if entry.address not in known_btc_addresses:
                new_addresses.append(entry.address)
                new_balances.append(entry.balance)
            else:
                existing_address_data.append(BlockchainAccountData(
                    address=entry.address,
                    label=None,
                    tags=xpub_data.tags,
                ))

        if len(existing_address_data) != 0:
            insert_tag_mappings(    # if we got tags add them to the existing addresses too
                cursor=self.db.conn.cursor(),
                data=existing_address_data,
                object_reference_key='address',
            )

        if len(new_addresses) != 0:
            self.chain_manager.add_blockchain_accounts(
                blockchain=SupportedBlockchain.BITCOIN,
                accounts=new_addresses,
                already_queried_balances=new_balances,
            )
            self.db.add_blockchain_accounts(
                blockchain=SupportedBlockchain.BITCOIN,
                account_data=[BlockchainAccountData(
                    address=x,
                    label=None,
                    tags=xpub_data.tags,
                ) for x in new_addresses],
            )
        self.db.ensure_xpub_mappings_exist(
            xpub=xpub_data.xpub.xpub,  # type: ignore
            derivation_path=xpub_data.derivation_path,
            derived_addresses_data=derived_addresses_data,
        )
        if not self.chain_manager.balances.is_queried(SupportedBlockchain.BITCOIN):
            self.chain_manager.query_balances(SupportedBlockchain.BITCOIN, ignore_cache=True)
        return self.chain_manager.get_balances_update()

    def delete_bitcoin_xpub(self, xpub_data: XpubData) -> 'BlockchainBalancesUpdate':
        """
        May raise:
        - InputError: If the xpub does not exist in the DB
        """
        # First try to delete the xpub, and if it does not exist raise InputError
        self.db.delete_bitcoin_xpub(xpub_data)
        self.chain_manager.sync_btc_accounts_with_db()
        return self.chain_manager.get_balances_update()
