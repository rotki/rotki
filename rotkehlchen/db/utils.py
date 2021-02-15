from enum import Enum
from sqlite3 import Cursor
from typing import TYPE_CHECKING, Dict, List, NamedTuple, Optional, Tuple, Union

from eth_utils import is_checksum_address
from typing_extensions import Literal

from rotkehlchen.accounting.structures import BalanceType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.balances.manual import ManuallyTrackedBalance
from rotkehlchen.chain.substrate.typing import KusamaAddress
from rotkehlchen.chain.substrate.utils import is_valid_kusama_address
from rotkehlchen.typing import (
    BlockchainAccountData,
    BTCAddress,
    ChecksumEthAddress,
    HexColorCode,
    ListOfBlockchainAddresses,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.misc import rgetattr

if TYPE_CHECKING:
    from rotkehlchen.chain.bitcoin.xpub import XpubData


class BlockchainAccounts(NamedTuple):
    eth: List[ChecksumEthAddress]
    btc: List[BTCAddress]
    ksm: List[KusamaAddress]

    def get(self, blockchain: SupportedBlockchain) -> ListOfBlockchainAddresses:
        if blockchain == SupportedBlockchain.BITCOIN:
            return self.btc
        if blockchain == SupportedBlockchain.ETHEREUM:
            return self.eth
        if blockchain == SupportedBlockchain.KUSAMA:
            return self.ksm
        raise AssertionError(f'Unsupported blockchain: {blockchain}')


class DBAssetBalance(NamedTuple):
    category: BalanceType
    time: Timestamp
    asset: Asset
    amount: str
    usd_value: str


class SingleDBAssetBalance(NamedTuple):
    category: BalanceType
    time: Timestamp
    amount: str
    usd_value: str


class LocationData(NamedTuple):
    time: Timestamp
    location: str  # Location serialized in a DB enum
    usd_value: str


class Tag(NamedTuple):
    name: str
    description: Optional[str]
    background_color: HexColorCode
    foreground_color: HexColorCode

    def serialize(self) -> Dict[str, str]:
        return self._asdict()  # pylint: disable=no-member


class DBStartupAction(Enum):
    NOTHING = 1
    UPGRADE_3_4 = 2
    STUCK_4_3 = 3


def str_to_bool(s: str) -> bool:
    return s == 'True'


def form_query_to_filter_timestamps(
        query: str,
        timestamp_attribute: str,
        from_ts: Optional[Timestamp],
        to_ts: Optional[Timestamp],
) -> Tuple[str, Union[Tuple, Tuple[Timestamp], Tuple[Timestamp, Timestamp]]]:
    """Formulates the query string and its bindings to filter for timestamps"""
    got_from_ts = from_ts is not None
    got_to_ts = to_ts is not None
    if got_from_ts or got_to_ts:
        query += ' WHERE ' if 'WHERE' not in query else 'AND '

    filters = []
    bindings = []
    if got_from_ts:
        filters.append(f'{timestamp_attribute} >= ?')
        bindings.append(from_ts)
    if got_to_ts:
        filters.append(f'{timestamp_attribute} <= ?')
        bindings.append(to_ts)

    query += ' AND '.join(filters)
    query += f' ORDER BY {timestamp_attribute} ASC;'

    return query, tuple(bindings)


def deserialize_tags_from_db(val: Optional[str]) -> Optional[List[str]]:
    """Read tags from the DB and turn it into a List of tags"""
    if val is None:
        tags = None
    else:
        tags = val.split(',')
        if len(tags) == 1 and tags[0] == '':
            tags = None

    return tags


def insert_tag_mappings(
        cursor: Cursor,
        data: Union[List[ManuallyTrackedBalance], List[BlockchainAccountData], List['XpubData']],
        object_reference_keys: List[
            Literal['label', 'address', 'xpub.xpub', 'derivation_path'],
        ],
) -> None:
    """
    Inserts the tag mappings from a list of potential data entries. If multiple keys are given
    then the concatenation of their values is what goes in as the object reference.
    """
    mapping_tuples = []
    for entry in data:
        if entry.tags is not None:
            reference = ''
            for key in object_reference_keys:
                value = rgetattr(entry, key)
                if value is not None:
                    reference += value
            mapping_tuples.extend([(reference, tag) for tag in entry.tags])

    cursor.executemany(
        'INSERT INTO tag_mappings(object_reference, tag_name) VALUES (?, ?)', mapping_tuples,
    )


def is_valid_db_blockchain_account(
        blockchain: str,
        account: str,
) -> bool:
    """Validates a blockchain address already stored in DB.
    """
    if blockchain == SupportedBlockchain.BITCOIN.value:
        return True
    if blockchain == SupportedBlockchain.ETHEREUM.value:
        return is_checksum_address(account)
    if blockchain == SupportedBlockchain.KUSAMA.value:
        return is_valid_kusama_address(account)

    raise AssertionError(f'Unknown blockchain: {blockchain}')
