from dataclasses import dataclass
from functools import wraps
from operator import attrgetter
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Literal,
    NamedTuple,
    Optional,
    Protocol,
    TypeVar,
    Union,
    overload,
)

from eth_utils import is_checksum_address
from typing_extensions import Concatenate, ParamSpec

from rotkehlchen.accounting.structures.balance import BalanceType
from rotkehlchen.assets.asset import Asset, AssetWithOracles
from rotkehlchen.chain.accounts import BlockchainAccountData
from rotkehlchen.chain.substrate.utils import is_valid_substrate_address
from rotkehlchen.db.drivers.gevent import DBCursor
from rotkehlchen.fval import FVal
from rotkehlchen.types import (
    AssetMovementCategory,
    HexColorCode,
    Location,
    Price,
    SupportedBlockchain,
    Timestamp,
    TradeType,
)
from rotkehlchen.utils.misc import pairwise_longest, rgetattr, timestamp_to_date

if TYPE_CHECKING:
    from rotkehlchen.balances.manual import ManuallyTrackedBalance
    from rotkehlchen.chain.bitcoin.xpub import XpubData
    from rotkehlchen.db.dbhandler import DBHandler

P = ParamSpec('P')
T_co = TypeVar('T_co', covariant=True)


class MaybeInjectWriteCursor(Protocol[P, T_co]):
    @overload
    def __call__(self, write_cursor: 'DBCursor', *args: P.args, **kwargs: P.kwargs) -> T_co:
        ...

    @overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T_co:
        ...


def need_writable_cursor(path_to_context_manager: str) -> Callable[[Callable[Concatenate['DBHandler', 'DBCursor', P], T_co]], MaybeInjectWriteCursor[P, T_co]]:  # noqa: E501
    def _need_writable_cursor(method: Callable[Concatenate['DBHandler', 'DBCursor', P], T_co]) -> MaybeInjectWriteCursor[P, T_co]:  # noqa: E501
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
        def _impl(self: 'DBHandler', *args: Any, **kwargs: Any) -> T_co:
            if kwargs.get('write_cursor') or len(args) != 0 and isinstance(args[0], DBCursor):
                return method(self, *args, **kwargs)

            # else we need to wrap this in a new writable cursor
            with attrgetter(path_to_context_manager)(self)() as cursor:
                result = method(self, cursor, *args, **kwargs)

            return result

        return _impl  # type: ignore
    return _need_writable_cursor


class MaybeInjectCursor(Protocol[P, T_co]):
    @overload
    def __call__(self, cursor: 'DBCursor', *args: P.args, **kwargs: P.kwargs) -> T_co:
        ...

    @overload
    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> T_co:
        ...


def need_cursor(path_to_context_manager: str) -> Callable[[Callable[Concatenate['DBHandler', 'DBCursor', P], T_co]], MaybeInjectCursor[P, T_co]]:  # noqa: E501
    def _need_cursor(method: Callable[Concatenate['DBHandler', 'DBCursor', P], T_co]) -> MaybeInjectCursor[P, T_co]:  # noqa: E501
        """Wraps the method of DBHandler in a read cursor or uses one if passed.

        The method should:
        1. have the cursor as the first argument.
        2. **NOT HAVE** a cursor as the 2nd argument

        Typing guide: https://sobolevn.me/2021/12/paramspec-guide
        """
        @wraps(method)
        def _impl(self: 'DBHandler', *args: Any, **kwargs: Any) -> T_co:
            if kwargs.get('cursor') or len(args) != 0 and isinstance(args[0], DBCursor):
                return method(self, *args, **kwargs)

            # else we need to wrap this in a new read only cursor
            with attrgetter(path_to_context_manager)(self)() as cursor:
                result = method(self, cursor, *args, **kwargs)
            return result

        return _impl  # type: ignore
    return _need_cursor


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBAssetBalance:
    category: BalanceType
    time: Timestamp
    asset: Asset
    amount: FVal
    usd_value: FVal

    def serialize(
            self,
            currency_and_price: Optional[tuple[AssetWithOracles, Price]] = None,
            display_date_in_localtime: bool = True,
    ) -> dict[str, Union[str, int]]:
        """Serializes a `DBAssetBalance` to dict.
        It accepts an `export_data` tuple of the user's local currency and the value of the
        currency in USD e.g (EUR, 1.01). If provided, the data is serialized for human consumption.
        """
        if currency_and_price:
            return {
                'timestamp': timestamp_to_date(
                    ts=self.time,
                    formatstr='%Y-%m-%d %H:%M:%S',
                    treat_as_local=display_date_in_localtime,
                ),
                'category': self.category.serialize(),
                'asset': str(self.asset),
                'asset_symbol': self.asset.symbol_or_name(),
                'amount': str(self.amount),
                f'{currency_and_price[0].symbol.lower()}_value': str(self.usd_value * currency_and_price[1]),  # noqa: E501
            }
        return {
            'timestamp': int(self.time),
            'category': self.category.serialize(),
            'asset_identifier': str(self.asset.identifier),
            'amount': str(self.amount),
            'usd_value': str(self.usd_value),
        }

    def serialize_for_db(self) -> tuple[str, int, str, str, str]:
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
    def deserialize_from_db(cls, entry: tuple[str, int, str, str, str]) -> 'DBAssetBalance':
        """Takes a timed balance from the DB and turns it into a `DBAssetBalance` object.
        May raise:
        - DeserializationError if the category from the db is invalid.
        - UnknownAsset if the asset identifier is malformed.
        """
        return cls(
            category=BalanceType.deserialize_from_db(entry[0]),
            time=Timestamp(entry[1]),
            asset=Asset(entry[2]).check_existence(),
            amount=FVal(entry[3]),
            usd_value=FVal(entry[4]),
        )


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class SingleDBAssetBalance:
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
            currency_and_price: Optional[tuple[AssetWithOracles, Price]] = None,
            display_date_in_localtime: bool = True,
    ) -> dict[str, Union[str, int]]:
        if currency_and_price:
            return {
                'timestamp': timestamp_to_date(
                    ts=self.time,
                    formatstr='%Y-%m-%d %H:%M:%S',
                    treat_as_local=display_date_in_localtime,
                ),
                'location': Location.deserialize_from_db(self.location).serialize(),
                f'{currency_and_price[0].symbol.lower()}_value': str(FVal(self.usd_value) * currency_and_price[1]),   # noqa: E501
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

    def serialize(self) -> dict[str, str]:
        return self._asdict()  # pylint: disable=no-member


def str_to_bool(s: str) -> bool:
    return s == 'True'


def form_query_to_filter_timestamps(
        query: str,
        timestamp_attribute: str,
        from_ts: Optional[Timestamp],
        to_ts: Optional[Timestamp],
) -> tuple[str, Union[tuple, tuple[Timestamp], tuple[Timestamp, Timestamp]]]:
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


def deserialize_tags_from_db(val: Optional[str]) -> Optional[list[str]]:
    """Read tags from the DB and turn it into a List of tags"""
    if val is None:
        tags = None
    else:
        tags = val.split(',')
        if len(tags) == 1 and tags[0] == '':
            tags = None

    return tags


def _get_tag_reference(
        entry: Union['ManuallyTrackedBalance', BlockchainAccountData, 'XpubData'],
        object_reference_keys: list[
            Literal['id', 'chain', 'address', 'xpub.xpub', 'derivation_path'],
        ],
) -> str:
    reference = ''
    for key in object_reference_keys:
        value = rgetattr(entry, key)
        if value is not None:  # value.value is for SupportedBlockchain
            reference += str(value) if key != 'chain' else value.value
    return reference


def _prepare_tag_mappings(
        entry: Union['ManuallyTrackedBalance', BlockchainAccountData, 'XpubData'],
        object_reference_keys: list[
            Literal['id', 'chain', 'address', 'xpub.xpub', 'derivation_path'],
        ],
) -> list[tuple[str, str]]:
    """Common function to prepare tag mappings. Caller has to make sure entry.tags is not None"""
    mapping_tuples = []
    reference = _get_tag_reference(entry, object_reference_keys)
    mapping_tuples.extend([(reference, tag) for tag in entry.tags])  # type: ignore[union-attr]
    return mapping_tuples


def insert_tag_mappings(
        write_cursor: 'DBCursor',
        data: Union[list['ManuallyTrackedBalance'], list[BlockchainAccountData], list['XpubData']],
        object_reference_keys: list[
            Literal['id', 'chain', 'address', 'xpub.xpub', 'derivation_path'],
        ],
) -> None:
    """
    Inserts the tag mappings from a list of potential data entries. If multiple keys are given
    then the concatenation of their values is what goes in as the object reference.
    """
    mapping_tuples = []
    for entry in data:
        if entry.tags is not None:
            mapping_tuples.extend(_prepare_tag_mappings(entry, object_reference_keys))

    write_cursor.executemany(
        'INSERT OR IGNORE INTO tag_mappings(object_reference, tag_name) VALUES (?, ?)', mapping_tuples,  # noqa: E501
    )


def replace_tag_mappings(
        write_cursor: 'DBCursor',
        data: Union[list['ManuallyTrackedBalance'], list[BlockchainAccountData], list['XpubData']],
        object_reference_keys: list[
            Literal['id', 'chain', 'address', 'xpub.xpub', 'derivation_path'],
        ],
) -> None:
    """Just like insert_tag_mappings but first deletes all existing mappings"""
    insert_tuples = []
    delete_tuples = []
    for entry in data:
        # Always delete current tags even if there are no new tags.
        delete_tuples.append((_get_tag_reference(entry, object_reference_keys),))
        if entry.tags is not None:
            insert_tuples.extend(_prepare_tag_mappings(entry, object_reference_keys))

    write_cursor.executemany(
        'DELETE FROM tag_mappings WHERE object_reference = ?;', delete_tuples,
    )
    write_cursor.executemany(
        'INSERT OR IGNORE INTO tag_mappings(object_reference, tag_name) VALUES (?, ?)', insert_tuples,  # noqa: E501
    )


def is_valid_db_blockchain_account(
        blockchain: SupportedBlockchain,
        account: str,
) -> bool:
    """Validates a blockchain address already stored in DB."""
    if blockchain == SupportedBlockchain.BITCOIN:
        return True
    if blockchain == SupportedBlockchain.BITCOIN_CASH:
        return True
    if blockchain.is_evm():
        return is_checksum_address(account)
    if blockchain.is_substrate():  # mypy does not understand the type narrowing here
        return is_valid_substrate_address(blockchain, account)  # type: ignore[arg-type]

    raise AssertionError(f'Should not store blockchain: {blockchain} addresses in the DB')


def _append_or_combine(balances: list[SingleDBAssetBalance], entry: SingleDBAssetBalance) -> list[SingleDBAssetBalance]:  # noqa: E501
    """Append entry to balances or combine with last if timestamp is the same"""
    if len(balances) == 0 or balances[-1].time != entry.time:
        balances.append(entry)
    else:
        balances[-1].amount += entry.amount
        balances[-1].usd_value += entry.usd_value

    return balances


def combine_asset_balances(balances: list[SingleDBAssetBalance]) -> list[SingleDBAssetBalance]:
    """Returns a list with all balances of the same timestamp combined"""
    new_balances: list[SingleDBAssetBalance] = []
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


def table_exists(cursor: 'DBCursor', name: str) -> bool:
    return cursor.execute(
        'SELECT COUNT(*) FROM sqlite_master WHERE type="table" AND name=?', (name,),
    ).fetchone()[0] == 1


DBTupleType = Literal[
    'trade',
    'asset_movement',
    'margin_position',
    'evm_transaction',
    'evm_internal_transaction',
]


def db_tuple_to_str(
        data: tuple[Any, ...],
        tuple_type: DBTupleType,
) -> str:
    """Turns a tuple DB entry for trade, or asset_movement into a user readable string

    This is only intended for error messages.
    """
    if tuple_type == 'trade':
        return (
            f'{TradeType.deserialize_from_db(data[5])} trade with id {data[0]} '
            f'in {Location.deserialize_from_db(data[2])} and base/quote asset {data[3]} / '
            f'{data[4]} at timestamp {data[1]}'
        )
    if tuple_type == 'asset_movement':
        return (
            f'{AssetMovementCategory.deserialize_from_db(data[2])} of '
            f'{data[4]} with id {data[0]} '
            f'in {Location.deserialize_from_db(data[1])} at timestamp {data[3]}'
        )
    if tuple_type == 'margin_position':
        return (
            f'Margin position with id {data[0]} in {Location.deserialize_from_db(data[1])} '
            f'for {data[5]} closed at timestamp {data[3]}'
        )

    # else can only be evm transaction
    assert tuple_type == 'evm_transaction', 'only DBTupleType possible here is evm_transaction'
    return f'EVM transaction with hash 0x{data[0].hex()} and chain id {data[1]}'


def protect_password_sqlcipher(password: str) -> str:
    """A double quote in the password would close the string. To escape it double it

    source: https://stackoverflow.com/a/603579/110395
"""
    return password.replace(r'"', r'""')


def update_table_schema(
        write_cursor: 'DBCursor',
        table_name: str,
        schema: str,
        insert_columns: Optional[str] = None,
        insert_order: str = '',
        insert_where: Optional[str] = None,
) -> bool:
    """Update the schema of a given table. Need to provide:
    1. The name
    2. The schema
    3. The insert_columns of the old table that are to be inserted to the new one. If missing * is used
    4. Optionally an order of insertion parentheses in case not all are added or names changed.
    5. Optionally a WHERE statement for the insertion

    Also is made error-proof to simply create the table if the old one for some
    reason did not exist.

    Returns True if the table existed and insertions were made and False otherwise
    """  # noqa: E501
    new_table_name = f'{table_name}_new' if table_exists(write_cursor, table_name) else table_name
    select_insert_columns = '*' if insert_columns is None else insert_columns
    write_cursor.execute(f'CREATE TABLE IF NOT EXISTS {new_table_name} ({schema});')
    if new_table_name != table_name:
        insert_where = f' WHERE {insert_where}' if insert_where else ''
        write_cursor.execute(f'INSERT OR IGNORE INTO {new_table_name}{insert_order} SELECT {select_insert_columns} FROM {table_name}{insert_where}')  # noqa: E501
        write_cursor.execute(f'DROP TABLE {table_name}')
        write_cursor.execute(f'ALTER TABLE {new_table_name} RENAME TO {table_name}')
        return True

    return False
