import logging
from typing import TYPE_CHECKING, Any, Dict, List, Literal, NamedTuple, Optional, Tuple

from gevent.lock import Semaphore

from rotkehlchen.accounting.structures.balance import Balance
from rotkehlchen.chain.bitcoin import have_bitcoin_transactions
from rotkehlchen.chain.bitcoin.bch import have_bch_transactions
from rotkehlchen.chain.bitcoin.hdkey import HDKey
from rotkehlchen.constants.assets import A_BCH, A_BTC
from rotkehlchen.db.utils import insert_tag_mappings
from rotkehlchen.errors.misc import RemoteError
from rotkehlchen.fval import FVal
from rotkehlchen.inquirer import Inquirer
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import BlockchainAccountData, BTCAddress, SupportedBlockchain

if TYPE_CHECKING:
    from rotkehlchen.chain.aggregator import ChainsAggregator
    from rotkehlchen.db.drivers.gevent import DBCursor


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class XpubData(NamedTuple):
    xpub: HDKey
    blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH]
    derivation_path: Optional[str] = None
    label: Optional[str] = None
    tags: Optional[List[str]] = None

    def serialize_derivation_path_for_db(self) -> str:
        """
        In rotki we store non-existing path as None but in sql it must be ''
        https://stackoverflow.com/questions/43827629/why-does-sqlite-insert-duplicate-composite-primary-keys
        """
        return '' if self.derivation_path is None else self.derivation_path

    def serialize(self) -> Dict[str, Any]:
        return {
            'xpub': self.xpub.xpub,
            'blockchain': self.blockchain.value,
            'derivation_path': self.derivation_path,
            'label': self.label,
            'tags': self.tags,
        }

    def __hash__(self) -> int:
        """For uniqueness of an xpub we consider xpub + derivation path + blockchain"""
        return hash(self.xpub.xpub + (self.derivation_path if self.derivation_path else '') + self.blockchain.value)  # type: ignore  # noqa: E501

    def __eq__(self, other: Any) -> bool:
        """For uniqueness of an xpub we consider xpub + derivation path"""
        return hash(self) == hash(other)


def deserialize_derivation_path_for_db(path: str) -> Optional[str]:
    """
    In rotki we store non-existing path as None but in sql it must be ''
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
        gap_limit: int,
        blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
) -> List[XpubDerivedAddressData]:
    """May raise:
    - RemoteError: if blockstream/blockchain.info can't be reached
    """
    step_index = start_index
    addresses: List[XpubDerivedAddressData] = []
    should_continue = True
    while should_continue:
        batch_addresses: List[Tuple[int, BTCAddress]] = []
        for idx in range(step_index, step_index + gap_limit):
            child = root.derive_child(idx)
            batch_addresses.append((idx, child.address()))

        if blockchain == SupportedBlockchain.BITCOIN:
            have_tx_mapping = have_bitcoin_transactions([x[1] for x in batch_addresses])
        else:
            have_tx_mapping = have_bch_transactions([x[1] for x in batch_addresses])
        should_continue = False
        for idx, address in batch_addresses:
            have_tx, balance = have_tx_mapping[address]
            if have_tx:
                addresses.append(XpubDerivedAddressData(
                    account_index=account_index,
                    derived_index=idx,
                    address=address,
                    balance=balance,
                ))
                should_continue = True

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

        step_index += gap_limit

    return addresses


def _derive_addresses_from_xpub_data(
        xpub_data: XpubData,
        start_receiving_index: int,
        start_change_index: int,
        gap_limit: int,
) -> List[XpubDerivedAddressData]:
    """Derive all addresses from the xpub that have had transactions. Also includes
    any addresses until the biggest index derived addresses that have had no transactions.
    This is to make it easier to later derive and check more addresses

    May raise:
    - RemoteError: if blockstream/blockchain.info/haskoin and others can't be reached
    """
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
            gap_limit=gap_limit,
            blockchain=xpub_data.blockchain,
        ),
    )
    change_xpub = account_xpub.derive_child(1)
    addresses.extend(
        _derive_addresses_loop(
            account_index=1,
            start_index=start_change_index,
            root=change_xpub,
            gap_limit=gap_limit,
            blockchain=xpub_data.blockchain,
        ),
    )
    return addresses


class XpubManager():

    def __init__(self, chains_aggregator: 'ChainsAggregator'):
        self.chains_aggregator = chains_aggregator
        self.db = chains_aggregator.database
        self.lock = Semaphore()

    def _derive_xpub_addresses(
        self,
        xpub_data: XpubData,
        new_xpub: bool,
    ) -> None:
        """Derives new xpub addresses, and adds all those until the addresses that
        have not had any transactions to the tracked bitcoin addresses

        Should be called with the lock acquired

        May raise:
        - RemoteError: if blockstream/blockchain.info/haskoin and others can't be reached
        """
        with self.db.conn.read_ctx() as cursor:
            last_receiving_idx, last_change_idx = self.db.get_last_consecutive_xpub_derived_indices(cursor, xpub_data)  # noqa: E501
            derived_addresses_data = _derive_addresses_from_xpub_data(
                xpub_data=xpub_data,
                start_receiving_index=last_receiving_idx,
                start_change_index=last_change_idx,
                gap_limit=self.chains_aggregator.btc_derivation_gap_limit,
            )
            known_addresses = getattr(self.db.get_blockchain_accounts(cursor), xpub_data.blockchain.value.lower())  # noqa: E501

        new_addresses = []
        existing_address_data = []
        for entry in derived_addresses_data:
            if entry.address not in known_addresses:
                new_addresses.append(entry.address)
            elif new_xpub:
                existing_address_data.append(BlockchainAccountData(
                    address=entry.address,
                    label=None,
                    tags=xpub_data.tags,
                ))

        with self.db.user_write() as cursor:
            if new_xpub and xpub_data.tags:
                insert_tag_mappings(  # if we got tags add them to the xpub
                    write_cursor=cursor,
                    data=[xpub_data],
                    object_reference_keys=['xpub.xpub', 'derivation_path'],
                )
            if new_xpub and len(existing_address_data) != 0:
                insert_tag_mappings(  # if we got tags add them to the existing addresses too
                    write_cursor=cursor,
                    data=existing_address_data,
                    object_reference_keys=['address'],
                )

            if len(new_addresses) != 0:
                self.chains_aggregator.add_blockchain_accounts(
                    blockchain=xpub_data.blockchain,
                    accounts=new_addresses,
                )
                self.db.add_blockchain_accounts(
                    write_cursor=cursor,
                    blockchain=xpub_data.blockchain,
                    account_data=[BlockchainAccountData(
                        address=x,
                        label=None,
                        tags=xpub_data.tags,
                    ) for x in new_addresses],
                )
            self.db.ensure_xpub_mappings_exist(
                write_cursor=cursor,
                xpub_data=xpub_data,
                derived_addresses_data=derived_addresses_data,
            )

        # also add queried balances
        if xpub_data.blockchain == SupportedBlockchain.BITCOIN:
            balances = self.chains_aggregator.balances.btc
            asset_usd_price = Inquirer.find_usd_price(A_BTC)
        else:  # BCH
            balances = self.chains_aggregator.balances.bch
            asset_usd_price = Inquirer.find_usd_price(A_BCH)

        for entry in derived_addresses_data:
            new_balance = Balance(
                amount=entry.balance,
                usd_value=entry.balance * asset_usd_price,
            )
            balances[entry.address] = new_balance
        self.chains_aggregator.totals = self.chains_aggregator.balances.recalculate_totals()

    def add_bitcoin_xpub(
        self,
        xpub_data: XpubData,
    ) -> None:
        """
        May raise:
        - InputError: If the xpub already exists in the DB
        - TagConstraintError if any of the given account data contain unknown tags.
        - RemoteError if an external service such as blockstream/haskoin is queried and
          there is a problem with its query.
        """
        with self.lock:
            with self.db.user_write() as cursor:
                # First try to add the xpub, and if it already exists raise
                self.db.add_bitcoin_xpub(cursor, xpub_data=xpub_data)
                # Then add tags if not existing
                self.db.ensure_tags_exist(
                    cursor,
                    given_data=[xpub_data],
                    action='adding',
                    data_type='bitcoin xpub' if xpub_data.blockchain == SupportedBlockchain.BITCOIN else 'bitcoin cash xpub',  # noqa: 501
                )
                self._derive_xpub_addresses(xpub_data, new_xpub=True)

    def delete_bitcoin_xpub(
            self,
            write_cursor: 'DBCursor',
            xpub_data: XpubData,
    ) -> None:
        """
        Deletes an xpub from the DB, along with all derived addresses, xpub and tag mappings
        May raise:
        - InputError: If the xpub does not exist in the DB
        """
        with self.lock:
            # First try to delete the xpub, and if it does not exist raise InputError
            self.db.delete_bitcoin_xpub(write_cursor, xpub_data)
            self.chains_aggregator.sync_bitcoin_accounts_with_db(write_cursor, xpub_data.blockchain)  # noqa: E501

    def check_for_new_xpub_addresses(
        self,
        blockchain: Literal[SupportedBlockchain.BITCOIN, SupportedBlockchain.BITCOIN_CASH],
    ) -> None:
        """Checks all xpub addresses and sees if new addresses got used.
        If they did it adds them for tracking.
        """
        log.debug(f'Starting task for derivation of new {blockchain.value} xpub addresses')
        with self.db.conn.read_ctx() as cursor:
            xpubs = self.db.get_bitcoin_xpub_data(cursor, blockchain)
        with self.lock:
            for xpub_data in xpubs:
                try:
                    self._derive_xpub_addresses(xpub_data, new_xpub=False)
                except RemoteError as e:
                    log.warning(
                        f'Failed to derive new xpub addresses from xpub: {xpub_data.xpub.xpub} '
                        f'and derivation_path: {xpub_data.derivation_path} due to: {str(e)}',
                    )
                    continue

                log.debug(
                    f'Attempt to derive new addresses from xpub: {xpub_data.xpub.xpub} '
                    f'and derivation_path: {xpub_data.derivation_path} finished',
                )

    def edit_bitcoin_xpub(
            self,
            write_cursor: 'DBCursor',
            xpub_data: 'XpubData',
    ) -> None:
        with self.lock:
            # Update the xpub label
            self.db.edit_bitcoin_xpub(write_cursor, xpub_data)
            # Then add tags if not existing
            self.db.ensure_tags_exist(
                write_cursor,
                given_data=[xpub_data],
                action='editing',
                data_type='bitcoin xpub' if xpub_data.blockchain == SupportedBlockchain.BITCOIN else 'bitcoin cash xpub',  # noqa: 501
            )
