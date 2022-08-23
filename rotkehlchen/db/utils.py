from dataclasses import dataclass
from functools import wraps
from operator import attrgetter
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Literal,
    NamedTuple,
    Optional,
    Protocol,
    Tuple,
    TypeVar,
    Union,
    overload,
)

from eth_utils import is_checksum_address
from typing_extensions import Concatenate, ParamSpec

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.chain.substrate.types import KusamaAddress, PolkadotAddress
from rotkehlchen.chain.substrate.utils import is_valid_kusama_address, is_valid_polkadot_address
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    BlockchainAccountData,
    BTCAddress,
    ChecksumEvmAddress,
    HexColorCode,
    ListOfBlockchainAddresses,
    Location,
    Price,
    SupportedBlockchain,
    Timestamp,
)
from rotkehlchen.utils.misc import pairwise_longest, rgetattr, timestamp_to_date

if TYPE_CHECKING:
    from rotkehlchen.balances.manual import ManuallyTrackedBalance
    from rotkehlchen.chain.bitcoin.xpub import XpubData
    from rotkehlchen.db.dbhandler import DBHandler

P = ParamSpec('P')
T = TypeVar('T', covariant=True)


class MaybeInjectWriteCursor(Protocol[P, T]):
    @overload
    def __call__(self, write_cursor: 'DBCursor', *args: P.args, **kwargs: P.kwargs) -> T:
        ...

    @overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        ...


def need_writable_cursor(path_to_context_manager: str) -> Callable[[Callable[Concatenate['DBHandler', 'DBCursor', P], T]], MaybeInjectWriteCursor[P, T]]:  # noqa: E501
    def _need_writable_cursor(method: Callable[Concatenate['DBHandler', 'DBCursor', P], T]) -> MaybeInjectWriteCursor[P, T]:  # noqa: E501
        """Wraps the method of a class in a write cursor or uses one if passed.

        The method should:
        1. have the write_cursor as the first argument.
        2. **NOT HAVE** a cursor as the 2nd argument

        The class should have something that would return a cursor context manager

        Typing guide: https://sobolevn.me/2021/12/paramspec-guide

        Keeping this only as an advanced example for typing and not using
        it much as I did not wanna add extra if checks in heavy calls
        """
        @wraps(method)
        def _impl(self: 'DBHandler', *args: Any, **kwargs: Any) -> T:
            if kwargs.get('write_cursor') or len(args) != 0 and isinstance(args[0], DBCursor):
                return method(self, *args, **kwargs)

            # else we need to wrap this in a new writable cursor
            with attrgetter(path_to_context_manager)(self)() as cursor:
                result = method(self, cursor, *args, **kwargs)

            return result

        return _impl  # type: ignore
    return _need_writable_cursor


class MaybeInjectCursor(Protocol[P, T]):
    @overload
    def __call__(self, cursor: 'DBCursor', *args: P.args, **kwargs: P.kwargs) -> T:
        ...

    @overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T:
        ...


def need_cursor(path_to_context_manager: str) -> Callable[[Callable[Concatenate['DBHandler', 'DBCursor', P], T]], MaybeInjectCursor[P, T]]:  # noqa: E501
    def _need_cursor(method: Callable[Concatenate['DBHandler', 'DBCursor', P], T]) -> MaybeInjectCursor[P, T]:  # noqa: E501
        """Wraps the method of DBHandler in a read cursor or uses one if passed.

        The method should:
        1. have the cursor as the first argument.
        2. **NOT HAVE** a cursor as the 2nd argument

        Typing guide: https://sobolevn.me/2021/12/paramspec-guide
        """
        @wraps(method)
        def _impl(self: 'DBHandler', *args: Any, **kwargs: Any) -> T:
            if kwargs.get('cursor') or len(args) != 0 and isinstance(args[0], DBCursor):
                return method(self, *args, **kwargs)

            # else we need to wrap this in a new read only cursor
            with attrgetter(path_to_context_manager)(self)() as cursor:
                result = method(self, cursor, *args, **kwargs)
            return result

        return _impl  # type: ignore
    return _need_cursor


class BlockchainAccounts(NamedTuple):
    eth: List[ChecksumEvmAddress]
    btc: List[BTCAddress]
    bch: List[BTCAddress]
    ksm: List[KusamaAddress]
    dot: List[PolkadotAddress]
    avax: List[ChecksumEvmAddress]

    def get(self, blockchain: SupportedBlockchain) -> ListOfBlockchainAddresses:
        if blockchain == SupportedBlockchain.BITCOIN:
            return self.btc
        if blockchain == SupportedBlockchain.BITCOIN_CASH:
            return self.bch
        if blockchain == SupportedBlockchain.ETHEREUM:
            return self.eth
        if blockchain == SupportedBlockchain.KUSAMA:
            return self.ksm
        if blockchain == SupportedBlockchain.POLKADOT:
            return self.dot
        if blockchain == SupportedBlockchain.AVALANCHE:
            return self.avax

        raise AssertionError(f'Unsupported blockchain: {blockchain}')


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBAssetBalance:
    category: BalanceType
    time: Timestamp
    asset: Asset
    amount: FVal
    usd_value: FVal

    def serialize(
            self,
            export_data: Optional[Tuple[Asset, Price]] = None,
    ) -> Dict[str, Union[str, int]]:
        """Serializes a `DBAssetBalance` to dict.
        It accepts an `export_data` tuple of the user's local currency and the value of the
        currency in USD e.g (EUR, 1.01). If provided, the data is serialized for human consumption.
        """
        if export_data:
            return {
                'timestamp': timestamp_to_date(self.time, '%Y-%m-%d %H:%M:%S'),
                'category': self.category.serialize(),
                'asset': str(self.asset),
                'amount': str(self.amount),
                f'{export_data[0].symbol.lower()}_value': str(self.usd_value * export_data[1]),  # noqa: E501
            }
        return {
            'timestamp': int(self.time),
            'category': self.category.serialize(),
            'asset_identifier': str(self.asset.identifier),
            'amount': str(self.amount),
            'usd_value': str(self.usd_value),
        }

    def serialize_for_db(self) -> Tuple[str, int, str, str, str]:
        """Serializes a `DBAssetBalance` to be written into the DB.
        (category, time, currency, amount, usd_value)
        """
        return (
            self.category.serialize_for_db(),
            self.time,
            self.asset.identifier,
            str(self.amount),
            str(self.usd_value),
        )

    @classmethod
    def deserialize_from_db(cls, entry: Tuple[str, int, str, str, str]) -> 'DBAssetBalance':
        """Takes a timed balance from the DB and turns it into a `DBAssetBalance` object.
        May raise:
        - DeserializationError if the category from the db is invalid.
        - UnknownAsset if the asset identifier is malformed.
        """
        return cls(
            category=BalanceType.deserialize_from_db(entry[0]),
            time=Timestamp(entry[1]),
            asset=Asset(entry[2]),
            amount=FVal(entry[3]),
            usd_value=FVal(entry[4]),
        )


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class SingleDBAssetBalance():
    category: BalanceType
    time: Timestamp
    amount: FVal
    usd_value: FVal


class LocationData(NamedTuple):
    time: Timestamp
    location: str  # Location serialized in a DB enum
    usd_value: str

    def serialize(
            self,
            export_data: Optional[Tuple[Asset, Price]] = None,
    ) -> Dict[str, Union[str, int]]:
        if export_data:
            return {
                'timestamp': timestamp_to_date(self.time, '%Y-%m-%d %H:%M:%S'),
                'location': Location.deserialize_from_db(self.location).serialize(),
                f'{export_data[0].symbol.lower()}_value': str(FVal(self.usd_value) * export_data[1]),   # noqa: 501
            }
        return {
            'timestamp': int(self.time),
            'location': Location.deserialize_from_db(self.location).serialize(),
            'usd_value': self.usd_value,
        }


class Tag(NamedTuple):
    name: str
    description: Optional[str]
    background_color: HexColorCode
    foreground_color: HexColorCode

    def serialize(self) -> Dict[str, str]:
        return self._asdict()  # pylint: disable=no-member


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
        write_cursor: 'DBCursor',
        data: Union[List['ManuallyTrackedBalance'], List[BlockchainAccountData], List['XpubData']],
        object_reference_keys: List[
            Literal['id', 'address', 'xpub.xpub', 'derivation_path'],
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
                    reference += str(value)
            mapping_tuples.extend([(reference, tag) for tag in entry.tags])

    write_cursor.executemany(
        'INSERT INTO tag_mappings(object_reference, tag_name) VALUES (?, ?)', mapping_tuples,
    )


def is_valid_db_blockchain_account(
        blockchain: str,
        account: str,
) -> bool:
    """Validates a blockchain address already stored in DB."""
    if blockchain == SupportedBlockchain.BITCOIN.value:
        return True
    if blockchain == SupportedBlockchain.BITCOIN_CASH.value:
        return True
    if blockchain in (SupportedBlockchain.ETHEREUM.value, SupportedBlockchain.AVALANCHE.value):
        return is_checksum_address(account)
    if blockchain == SupportedBlockchain.KUSAMA.value:
        return is_valid_kusama_address(account)
    if blockchain == SupportedBlockchain.POLKADOT.value:
        return is_valid_polkadot_address(account)

    raise AssertionError(f'Unknown blockchain: {blockchain}')


def _append_or_combine(balances: List[SingleDBAssetBalance], entry: SingleDBAssetBalance) -> List[SingleDBAssetBalance]:  # noqa: E501
    """Append entry to balances or combine with last if timestamp is the same"""
    if len(balances) == 0 or balances[-1].time != entry.time:
        balances.append(entry)
    else:
        balances[-1].amount += entry.amount
        balances[-1].usd_value += entry.usd_value

    return balances


def combine_asset_balances(balances: List[SingleDBAssetBalance]) -> List[SingleDBAssetBalance]:
    """Returns a list with all balances of the same timestamp combined"""
    new_balances: List[SingleDBAssetBalance] = []
    for balance, next_balance in pairwise_longest(balances):
        if next_balance is None:
            new_balances = _append_or_combine(new_balances, balance)
            break

        if balance.time != next_balance.time:
            new_balances = _append_or_combine(new_balances, balance)
            new_balances.append(next_balance)
        else:
            balance.amount += next_balance.amount
            balance.usd_value += next_balance.usd_value
            new_balances = _append_or_combine(new_balances, balance)

    return new_balances
