import logging
from abc import ABC, abstractmethod
from collections.abc import Collection, Sequence
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Generic, Literal, NamedTuple, Self, TypeVar

from rotkehlchen.accounting.types import SchemaEventType
from rotkehlchen.api.v1.types import IncludeExcludeFilterData
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.ignored_assets_handling import IgnoredAssetsHandling
from rotkehlchen.assets.types import AssetType
from rotkehlchen.chain.ethereum.modules.nft.structures import NftLpHandling
from rotkehlchen.chain.evm.types import EvmAccount
from rotkehlchen.db.constants import (
    ETH_STAKING_EVENT_FIELDS,
    EVM_EVENT_FIELDS,
    EVMTX_DECODED,
    HISTORY_BASE_ENTRY_FIELDS,
    HISTORY_MAPPING_KEY_STATE,
    HISTORY_MAPPING_STATE_CUSTOMIZED,
)
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.globaldb.cache import compute_cache_key
from rotkehlchen.history.events.structures.base import HistoryBaseEntryType
from rotkehlchen.history.events.structures.evm_event import EvmProduct
from rotkehlchen.history.events.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    CacheType,
    ChainID,
    ChecksumEvmAddress,
    EVMTxHash,
    Location,
    OptionalBlockchainAddress,
    OptionalChainAddress,
    SupportedBlockchain,
    Timestamp,
    TradeType,
)
from rotkehlchen.utils.misc import ts_now


class InvalidFilter(Exception):
    """Raised if an invalid filter combination has been given"""


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


ALL_EVENTS_DATA_JOIN = """FROM history_events
LEFT JOIN evm_events_info ON history_events.identifier=evm_events_info.identifier
LEFT JOIN eth_staking_events_info ON history_events.identifier=eth_staking_events_info.identifier """  # noqa: E501
EVM_EVENT_JOIN = 'FROM history_events INNER JOIN evm_events_info ON history_events.identifier=evm_events_info.identifier '  # noqa: E501
ETH_STAKING_EVENT_JOIN = 'FROM history_events INNER JOIN eth_staking_events_info ON history_events.identifier=eth_staking_events_info.identifier '  # noqa: E501
ETH_DEPOSIT_EVENT_JOIN = ALL_EVENTS_DATA_JOIN


T = TypeVar('T')
V = TypeVar('V')
T_FilterQ = TypeVar('T_FilterQ', bound='DBFilterQuery')
T_HistoryBaseEntryFilterQ = TypeVar('T_HistoryBaseEntryFilterQ', bound='HistoryBaseEntryFilterQuery')  # noqa: E501
T_EthSTakingFilterQ = TypeVar('T_EthSTakingFilterQ', bound='EthStakingEventFilterQuery')


class DBFilterOrder(NamedTuple):
    rules: list[tuple[str, bool]]
    case_sensitive: bool

    def prepare(self) -> str:
        querystr = 'ORDER BY '
        for idx, (attribute, ascending) in enumerate(self.rules):
            if idx != 0:
                querystr += ','
            if attribute in {'amount', 'fee', 'rate', 'last_price', 'last_price_asset', 'manual_price', 'pnl_taxable', 'pnl_free'}:  # noqa: E501
                order_by = f'CAST({attribute} AS REAL)'
            else:
                order_by = attribute

            if self.case_sensitive is False:
                querystr += f"{order_by} COLLATE NOCASE {'ASC' if ascending else 'DESC'}"
            else:
                querystr += f"{order_by} {'ASC' if ascending else 'DESC'}"

        return querystr


class DBFilterPagination(NamedTuple):
    limit: int | None
    offset: int | None

    def prepare(self) -> str:
        return f'LIMIT {self.limit or -1}' + (f' OFFSET {self.offset}' if self.offset else '')


class DBFilterGroupBy(NamedTuple):
    field_name: str

    def prepare(self) -> str:
        return f'GROUP BY {self.field_name}'


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBFilter:
    and_op: bool

    def prepare(self) -> tuple[list[str], Collection[Any]]:
        raise NotImplementedError('prepare should be implemented by subclasses')


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBNestedFilter(DBFilter):
    """Filter that allows combination of multiple subfilters with different operands."""
    filters: list[DBFilter]

    def prepare(self) -> tuple[list[str], list[Any]]:
        filterstrings = []
        bindings: list[Any] = []
        for single_filter in self.filters:
            filters, single_bindings = single_filter.prepare()
            if len(filters) == 0:
                continue

            operator = ' AND ' if single_filter.and_op else ' OR '
            filterstrings.append(f'({operator.join(filters)})')
            bindings.extend(single_bindings)

        operator = ' AND ' if self.and_op else ' OR '
        return [f'({operator.join(filterstrings)})'], bindings


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBTimestampFilter(DBFilter):
    from_ts: Timestamp | None = None
    to_ts: Timestamp | None = None
    scaling_factor: FVal | None = None
    timestamp_field: str | None = None

    def prepare(self) -> tuple[list[str], list[Any]]:
        filters = []
        bindings = []
        timestamp_field = 'timestamp'
        if self.timestamp_field is not None:
            timestamp_field = self.timestamp_field
        if self.from_ts is not None:
            filters.append(f'{timestamp_field} >= ?')
            from_ts = self.from_ts
            if self.scaling_factor is not None:
                from_ts = Timestamp((from_ts * self.scaling_factor).to_int(exact=False))
            bindings.append(from_ts)
        if self.to_ts is not None:
            filters.append(f'{timestamp_field} <= ?')
            to_ts = self.to_ts
            if self.scaling_factor is not None:
                to_ts = Timestamp((to_ts * self.scaling_factor).to_int(exact=False))
            bindings.append(to_ts)

        return filters, bindings


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBEvmTransactionJoinsFilter(DBFilter):
    """This join finds transactions involving any of the address/chain combos.
    Including internal ones. This uses the mappings we create in the DB at transaction
    addition to signify relevant addresses for a transaction.
    """
    accounts: list[EvmAccount]

    def prepare(self) -> tuple[list[str], list[Any]]:
        query_filters: list[str] = []
        bindings: list[ChecksumEvmAddress | int] = []
        query_filter_str = (
            'INNER JOIN evmtx_address_mappings WHERE '
            'evm_transactions.identifier=evmtx_address_mappings.tx_id AND ('
        )
        individual_queries = []
        for address, _ in self.accounts:  # chain not used here but accessed earlier up the chain
            individual_query = '(evmtx_address_mappings.address = ?'
            bindings.append(address)
            individual_query += ')'

            individual_queries.append(individual_query)

        query_filter_str += ' OR '.join(individual_queries)
        query_filters.append(query_filter_str + ')')

        query = f' {" ".join(query_filters)} '
        return [query], bindings


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBTransactionsPendingDecodingFilter(DBFilter):
    """
    This filter is used to find the ethereum transactions that have not been decoded yet
    using the query in `TRANSACTIONS_MISSING_DECODING_QUERY`. It allows filtering by chain.

    Due to the joining we need to check for either value being NULL (meaning no entry
    in evm_tx_mappings) or not having the DECODED value.
    """
    chain_id: ChainID | None

    def prepare(self) -> tuple[list[str], list[Any]]:
        query_filters = ['(B.tx_id IS NULL OR B.tx_id NOT IN (SELECT tx_id FROM evm_tx_mappings WHERE value=?))']  # noqa: E501
        bindings: list[int] = [EVMTX_DECODED]
        if self.chain_id is not None:
            bindings.append(self.chain_id.serialize_for_db())
            query_filters.append('C.chain_id=?')

        query = ' AND '.join(query_filters)
        return [query], bindings


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBEvmTransactionHashFilter(DBFilter):
    tx_hash: EVMTxHash | None = None

    def prepare(self) -> tuple[list[str], list[Any]]:
        if self.tx_hash is None:
            return [], []

        return ['evm_transactions.tx_hash=?'], [self.tx_hash]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBEvmChainIDFilter(DBFilter):
    chain_id: SUPPORTED_CHAIN_IDS | None = None
    table_name: str | None = None

    def prepare(self) -> tuple[list[str], list[Any]]:
        if self.chain_id is None:
            return [], []

        prefix = f'{self.table_name}.' if self.table_name else ''
        return [f'{prefix}chain_id=?'], [self.chain_id.serialize_for_db()]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBReportDataReportIDFilter(DBFilter):
    report_id: str | int | None = None

    def prepare(self) -> tuple[list[str], list[Any]]:
        if self.report_id is None:
            return [], []

        if isinstance(self.report_id, str):
            try:
                value = int(self.report_id)
            except DeserializationError as e:
                log.error(f'Failed to filter a DB transaction query by report_id: {e!s}')
                return [], []
        else:
            value = self.report_id

        return ['report_id=?'], [value]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBReportDataEventTypeFilter(DBFilter):
    event_type: str | SchemaEventType | None = None

    def prepare(self) -> tuple[list[str], list[Any]]:
        if self.event_type is None:
            return [], []

        if isinstance(self.event_type, str):
            try:
                value = SchemaEventType.deserialize_from_db(self.event_type)
            except DeserializationError as e:
                log.error(f'Failed to filter a DB transaction query by event_type: {e!s}')
                return [], []
        else:
            value = self.event_type

        return ['event_type=?'], [str(value)]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBLocationFilter(DBFilter):
    location: Location

    def prepare(self) -> tuple[list[str], list[Any]]:
        return ['location=?'], [self.location.serialize_for_db()]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBNullableLocationFilter(DBFilter):
    location: Location | None

    def prepare(self) -> tuple[list[str], list[Any]]:
        return (['location IS ?'], [None if self.location is None else self.location.serialize_for_db()])  # noqa: E501


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBSubStringFilter(DBFilter):
    field: str
    search_string: str

    def prepare(self) -> tuple[list[str], list[Any]]:
        return [f'{self.field} LIKE ?'], [f'%{self.search_string}%']


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBFilterQuery(ABC):
    and_op: bool
    filters: list[DBFilter]
    join_clause: DBFilter | None = None
    group_by: DBFilterGroupBy | None = None
    order_by: DBFilterOrder | None = None
    pagination: DBFilterPagination | None = None

    def prepare(
            self,
            with_pagination: bool = True,
            with_order: bool = True,
            with_group_by: bool = False,
            without_ignored_asset_filter: bool = False,
    ) -> tuple[str, list[Any]]:
        """Prepares a filter by converting the filters to a query string

        Can be configured to:
        - with_pagination: Use or not the pagination filters
        - with_order: Use or not the order by filters
        - with_group_by: Use or not the group by filters
        - without_ignored_asset_filter: This is only for history events query and since we have
        quite a complicated query in the backend to count the limited grouped history events, there
        is no need to rerun the ignored assets filter as it's already part of the inner
        query in order to not count ignored/spam assets in the limit of free events.
        TODO: Quite hacky. Improve this.
        """
        query_parts = []
        bindings: list[Any] = []
        filterstrings = []

        if self.join_clause is not None:
            join_querystr, single_bindings = self.join_clause.prepare()
            query_parts.append(join_querystr[0])
            bindings.extend(single_bindings)

        for fil in self.filters:
            if without_ignored_asset_filter and isinstance(fil, DBIgnoredAssetsFilter):
                continue  # skip subtable select filter as it's already applied

            filters, single_bindings = fil.prepare()
            if len(filters) == 0:
                continue

            operator = ' AND ' if fil.and_op else ' OR '
            filterstrings.append(f'({operator.join(filters)})')
            bindings.extend(single_bindings)

        if len(filterstrings) != 0:
            operator = ' AND ' if self.and_op else ' OR '
            filter_query = f'{"WHERE " if self.join_clause is None else "AND ("}{operator.join(filterstrings)}{"" if self.join_clause is None else ")"}'  # noqa: E501
            query_parts.append(filter_query)

        if with_group_by and self.group_by is not None:
            groupby_query = self.group_by.prepare()
            query_parts.append(groupby_query)

        if with_order and self.order_by is not None:
            orderby_query = self.order_by.prepare()
            query_parts.append(orderby_query)

        if with_pagination and self.pagination is not None:
            pagination_query = self.pagination.prepare()
            query_parts.append(pagination_query)

        return ' '.join(query_parts), bindings

    @classmethod
    def create(
            cls,
            and_op: bool,
            limit: int | None,
            offset: int | None,
            order_by_case_sensitive: bool = True,
            order_by_rules: list[tuple[str, bool]] | None = None,
            group_by_field: str | None = None,
    ) -> Self:
        if limit is None or offset is None:
            pagination = None
        else:
            pagination = DBFilterPagination(limit=limit, offset=offset)

        group_by = None
        if group_by_field is not None:
            group_by = DBFilterGroupBy(field_name=group_by_field)

        order_by = None
        if order_by_rules is not None:
            order_by = DBFilterOrder(rules=order_by_rules, case_sensitive=order_by_case_sensitive)

        return cls(
            and_op=and_op,
            filters=[],
            group_by=group_by,
            order_by=order_by,
            pagination=pagination,
        )


class FilterWithTimestamp:

    timestamp_filter: DBTimestampFilter

    @property
    def from_ts(self) -> Timestamp:
        if self.timestamp_filter.from_ts is None:
            return Timestamp(0)

        return self.timestamp_filter.from_ts

    @from_ts.setter
    def from_ts(self, from_ts: Timestamp | None) -> None:
        self.timestamp_filter.from_ts = from_ts

    @property
    def to_ts(self) -> Timestamp:
        if self.timestamp_filter.to_ts is None:
            return ts_now()

        return self.timestamp_filter.to_ts

    @to_ts.setter
    def to_ts(self, to_ts: Timestamp | None) -> None:
        self.timestamp_filter.to_ts = to_ts


class FilterWithLocation:

    location_filter: DBLocationFilter | None = None

    @property
    def location(self) -> Location | None:
        if self.location_filter is None:
            return None

        return self.location_filter.location


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class EvmTransactionsFilterQuery(DBFilterQuery, FilterWithTimestamp):

    @property
    def accounts(self) -> list[EvmAccount] | None:
        if not isinstance(self.join_clause, DBEvmTransactionJoinsFilter):
            return None

        return self.join_clause.accounts

    @property
    def chain_id(self) -> SUPPORTED_CHAIN_IDS | None:
        if isinstance(self.filters[-1], DBEvmChainIDFilter):
            return self.filters[-1].chain_id
        return None

    @classmethod
    def make(
            cls: type['EvmTransactionsFilterQuery'],
            and_op: bool = True,
            order_by_rules: list[tuple[str, bool]] | None = None,
            limit: int | None = None,
            offset: int | None = None,
            accounts: list[EvmAccount] | None = None,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
            tx_hash: EVMTxHash | None = None,
            chain_id: SUPPORTED_CHAIN_IDS | None = None,
    ) -> 'EvmTransactionsFilterQuery':
        """May raise:
        - InvalidFilter for invalid combination of filters
        """
        if order_by_rules is None:
            order_by_rules = [('timestamp', True)]

        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        # Create the timestamp filter so that from/to ts works. But add it only if needed
        filter_query.timestamp_filter = DBTimestampFilter(
            and_op=True,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        filters: list[DBFilter] = []
        if tx_hash is not None:  # tx_hash means single result so make it as single filter
            filters.append(DBEvmTransactionHashFilter(and_op=True, tx_hash=tx_hash))
            if chain_id is not None:  # keep it as last (see chain_id property of this filter)
                filters.append(DBEvmChainIDFilter(and_op=True, chain_id=chain_id, table_name='evm_transactions'))  # noqa: E501

        else:
            if accounts is not None:
                if filter_query.join_clause is not None:  # atm "should not happen"
                    raise InvalidFilter('Unable to filter by account due to conflicting filter')

                filter_query.join_clause = DBEvmTransactionJoinsFilter(
                    and_op=False,
                    accounts=accounts,
                )

            filters.append(filter_query.timestamp_filter)
            if chain_id is not None:  # keep it as last (see chain_id property of this filter)
                filters.append(DBEvmChainIDFilter(
                    and_op=True,
                    table_name='evm_transactions',
                    chain_id=chain_id,
                ))

        filter_query.filters = filters
        return filter_query


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBAssetFilter(DBFilter):
    asset: Asset
    asset_key: str

    def prepare(self) -> tuple[list[str], list[Any]]:
        return [f'{self.asset_key}=?'], [self.asset.identifier]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBIgnoreValuesFilter(DBFilter):
    column: str
    values: Collection[Any]

    def prepare(self) -> tuple[list[str], Collection[Any]]:
        if len(self.values) == 0:
            return [], []
        return [f'{self.column} NOT IN ({", ".join(["?"] * len(self.values))})'], self.values


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBEth2ValidatorIndicesFilter(DBFilter):
    """A filter for Eth2 validator indices"""
    validators: set[int] | None

    def prepare(self) -> tuple[list[str], list[Any]]:
        if self.validators is None:
            return [], []
        questionmarks = '?' * len(self.validators)
        return [f'validator_index IN ({",".join(questionmarks)})'], list(self.validators)


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBTypeFilter(DBFilter):
    """A filter for type/category/HistoryBaseEntry enums"""
    filter_types: list[TradeType]
    type_key: Literal['type', 'subtype', 'category']

    def prepare(self) -> tuple[list[str], list[Any]]:
        if len(self.filter_types) == 1:
            return [f'{self.type_key}=?'], [self.filter_types[0].serialize_for_db()]
        return (
            [f'{self.type_key} IN ({", ".join(["?"] * len(self.filter_types))})'],
            [entry.serialize_for_db() for entry in self.filter_types],
        )


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBNotEqualFilter(DBFilter):
    """Filter a column by comparing its column to its value for inequality"""
    column: str
    value: str | (bytes | (int | bool))
    alias: str | None = None

    def key_name(self) -> str:
        key_name = self.column
        if self.alias is not None:
            key_name = f'{self.alias}.{key_name}'

        return key_name

    def prepare(self) -> tuple[list[str], list[Any]]:
        return [f'{self.key_name()}!=?'], [self.value]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBEqualsFilter(DBNotEqualFilter):
    """Filter a column by comparing its column to its value for equality.
    For nullable columns that's where we want to include the null rows set
    include_null_values to true.
    """
    include_null_values: bool = False

    def prepare(self) -> tuple[list[str], list[Any]]:
        key_name = self.key_name()
        if self.include_null_values is False:
            return [f'{key_name}=?'], [self.value]

        return [f'{key_name}=? OR ({key_name} IS NULL)'], [self.value]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBMultiValueFilter(DBFilter, Generic[T]):
    """Filter a column having a value out of a selection of values"""
    column: str
    values: Sequence[T]
    operator: Literal['IN', 'NOT IN'] = 'IN'

    def prepare(self) -> tuple[list[str], Sequence[T]]:
        placeholders = ', '.join(['?'] * len(self.values))
        query = f'{self.column} {self.operator} ({placeholders})'
        if self.operator == 'NOT IN':  # NOT IN needs special treatment of NULL
            query = f'({query} OR {self.column} IS NULL)'  # Enclose in parentheses so OR works when combined with other filters  # noqa: E501

        return [query], self.values


class DBMultiStringFilter(DBMultiValueFilter[str]):
    """Filter a column having a string value out of a selection of values"""


class DBMultiBytesFilter(DBMultiValueFilter[bytes]):
    """Filter a column having a bytes value out of a selection of values"""


class DBMultiIntegerFilter(DBMultiValueFilter[int]):
    """Filter a column having an integer value out of a selection of values"""


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBOptionalChainAddressesFilter(DBFilter):
    """Filter the address column by a selection of optional chain addresses"""
    optional_chain_addresses: (
        list[OptionalChainAddress] |
        list[OptionalBlockchainAddress] |
        None
    )

    def prepare(self) -> tuple[list[str], list[str]]:
        query_filters = []
        bindings: list[str | ChecksumEvmAddress] = []
        if self.optional_chain_addresses is not None:
            for optional_chain_address in self.optional_chain_addresses:
                query_part = 'address = ?'
                bindings.append(optional_chain_address.address)
                if optional_chain_address.blockchain is not None:
                    query_part += ' AND blockchain = ?'
                    bindings.append(optional_chain_address.blockchain.value)
                query_filters.append(query_part)
        return query_filters, bindings


class TradesFilterQuery(DBFilterQuery, FilterWithTimestamp, FilterWithLocation):

    @classmethod
    def make(
            cls: type['TradesFilterQuery'],
            and_op: bool = True,
            order_by_rules: list[tuple[str, bool]] | None = None,
            limit: int | None = None,
            offset: int | None = None,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
            base_assets: tuple[Asset, ...] | None = None,
            quote_assets: tuple[Asset, ...] | None = None,
            trade_type: list[TradeType] | None = None,
            location: Location | None = None,
            trades_idx_to_ignore: set[str] | None = None,
            exclude_ignored_assets: bool = False,
    ) -> 'TradesFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('timestamp', True)]

        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filters: list[DBFilter] = []
        if base_assets is not None:
            if len(base_assets) == 1:
                filters.append(
                    DBAssetFilter(and_op=True, asset=base_assets[0], asset_key='base_asset'),
                )
            else:
                filters.append(
                    DBMultiStringFilter(
                        and_op=True,
                        column='base_asset',
                        values=[asset.identifier for asset in base_assets],
                    ),
                )
        if quote_assets is not None:
            if len(quote_assets) == 1:
                filters.append(
                    DBAssetFilter(and_op=True, asset=quote_assets[0], asset_key='quote_asset'),
                )
            else:
                filters.append(
                    DBMultiStringFilter(
                        and_op=True,
                        column='quote_asset',
                        values=[asset.identifier for asset in quote_assets],
                    ),
                )
        if trade_type is not None:
            filters.append(DBTypeFilter(and_op=True, filter_types=trade_type, type_key='type'))
        if location is not None:
            filter_query.location_filter = DBLocationFilter(and_op=True, location=location)
            filters.append(filter_query.location_filter)
        if trades_idx_to_ignore is not None:
            filters.append(DBIgnoreValuesFilter(
                and_op=True,
                column='id',
                values=trades_idx_to_ignore,
            ))

        if exclude_ignored_assets is True:
            filters.extend((
                DBIgnoredAssetsFilter(
                    and_op=True,
                    asset_key='base_asset',
                    operator='NOT IN',
                ), DBIgnoredAssetsFilter(
                    and_op=True,
                    asset_key='quote_asset',
                    operator='NOT IN',
                )))

        filter_query.timestamp_filter = DBTimestampFilter(
            and_op=True,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        filters.append(filter_query.timestamp_filter)
        filter_query.filters = filters
        return filter_query


class Eth2DailyStatsFilterQuery(DBFilterQuery, FilterWithTimestamp):

    @classmethod
    def make(
            cls: type['Eth2DailyStatsFilterQuery'],
            and_op: bool = True,
            order_by_rules: list[tuple[str, bool]] | None = None,
            limit: int | None = None,
            offset: int | None = None,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
            validator_indices: set[int] | None = None,
    ) -> 'Eth2DailyStatsFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('timestamp', True)]

        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filters: list[DBFilter] = []

        filter_query.timestamp_filter = DBTimestampFilter(
            and_op=True,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        filters.extend((
            filter_query.timestamp_filter,
            DBEth2ValidatorIndicesFilter(and_op=True, validators=validator_indices)))
        filter_query.filters = filters
        return filter_query


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class ReportDataFilterQuery(DBFilterQuery, FilterWithTimestamp):

    @property
    def report_id_filter(self) -> DBReportDataReportIDFilter | None:
        if len(self.filters) >= 1 and isinstance(self.filters[0], DBReportDataReportIDFilter):
            return self.filters[0]
        return None

    @property
    def event_type_filter(self) -> DBReportDataEventTypeFilter | None:
        if len(self.filters) >= 2 and isinstance(self.filters[1], DBReportDataEventTypeFilter):
            return self.filters[1]
        return None

    @property
    def report_id(self) -> str | int | None:
        report_id_filter = self.report_id_filter
        if report_id_filter is None:
            return None
        return report_id_filter.report_id

    @property
    def event_type(self) -> str | SchemaEventType | None:
        event_type_filter = self.event_type_filter
        if event_type_filter is None:
            return None
        return event_type_filter.event_type

    @classmethod
    def make(
            cls: type['ReportDataFilterQuery'],
            and_op: bool = True,
            order_by_rules: list[tuple[str, bool]] | None = None,
            limit: int | None = None,
            offset: int | None = None,
            report_id: int | None = None,
            event_type: str | None = None,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
    ) -> 'ReportDataFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('timestamp', True)]

        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filters: list[DBFilter] = []
        if report_id is not None:
            filters.append(DBReportDataReportIDFilter(and_op=True, report_id=report_id))
        if event_type is not None:
            filters.append(DBReportDataEventTypeFilter(and_op=True, event_type=event_type))

        filter_query.timestamp_filter = DBTimestampFilter(
            and_op=True,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        filters.append(filter_query.timestamp_filter)
        filter_query.filters = filters
        return filter_query


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBNullFilter(DBFilter):
    columns: list[str]
    verb: Literal['IS', 'IS NOT'] = 'IS'

    def prepare(self) -> tuple[list[str], list[Any]]:
        return [f'{column} {self.verb} NULL' for column in self.columns], []


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class HistoryEventCustomizedOnlyJoinsFilter(DBFilter):
    """This join finds customized history events (exclusively)."""
    def prepare(self) -> tuple[list[str], list[Any]]:
        query = (
            'INNER JOIN history_events_mappings '
            'ON history_events_mappings.parent_identifier = history_events_identifier '
            'WHERE history_events_mappings.name = ? AND history_events_mappings.value = ?'
        )
        bindings: list[str | int] = [HISTORY_MAPPING_KEY_STATE, HISTORY_MAPPING_STATE_CUSTOMIZED]
        return [query], bindings


class HistoryBaseEntryFilterQuery(DBFilterQuery, FilterWithTimestamp, FilterWithLocation, ABC):

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_rules: list[tuple[str, bool]] | None = None,
            limit: int | None = None,
            offset: int | None = None,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
            assets: tuple[Asset, ...] | None = None,
            event_types: list[HistoryEventType] | None = None,
            event_subtypes: list[HistoryEventSubType] | None = None,
            exclude_subtypes: list[HistoryEventSubType] | None = None,
            location: Location | None = None,
            location_labels: list[str] | None = None,
            excluded_locations: list[Location] | None = None,
            ignored_ids: list[str] | None = None,
            null_columns: list[str] | None = None,
            identifiers: list[int] | None = None,
            event_identifiers: list[str] | None = None,
            entry_types: IncludeExcludeFilterData | None = None,
            exclude_ignored_assets: bool = False,
            exclude_entire_event_group_on_ignored_asset: bool = True,
            customized_events_only: bool = False,
    ) -> Self:
        """May raise:
        - InvalidFilter for invalid combination of filters
        """
        if order_by_rules is None:
            order_by_rules = [('timestamp', True), ('sequence_index', True)]

        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
            group_by_field='event_identifier',
        )
        if customized_events_only is True:
            if filter_query.join_clause is not None:  # atm "should not happen"
                raise InvalidFilter('Unable to filter by customized events due to conflicting filter')  # noqa: E501

            filter_query.join_clause = HistoryEventCustomizedOnlyJoinsFilter(and_op=True)

        filters: list[DBFilter] = []
        if assets is not None:
            if len(assets) == 1:
                filters.append(DBAssetFilter(and_op=True, asset=assets[0], asset_key='asset'))
            else:
                filters.append(
                    DBMultiStringFilter(
                        and_op=True,
                        column='asset',
                        values=[asset.identifier for asset in assets],
                    ),
                )
        if entry_types is not None:
            filters.append(DBMultiIntegerFilter(
                and_op=True,
                column='entry_type',
                values=[x.value for x in entry_types.values],
                operator=entry_types.operator,
            ))
        if event_types is not None:
            filters.append(DBMultiStringFilter(
                and_op=True,
                column='type',
                values=[x.serialize() for x in event_types],
                operator='IN',
            ))
        if event_subtypes is not None:
            filters.append(DBMultiStringFilter(
                and_op=True,
                column='subtype',
                values=[x.serialize() for x in event_subtypes],
                operator='IN',
            ))
        if exclude_subtypes is not None:
            filters.append(DBMultiStringFilter(
                and_op=True,
                column='subtype',
                values=[x.serialize() for x in exclude_subtypes],
                operator='NOT IN',
            ))
        if location is not None:
            filter_query.location_filter = DBLocationFilter(and_op=True, location=location)
            filters.append(filter_query.location_filter)
        if excluded_locations is not None:
            filters.append(DBMultiStringFilter(
                and_op=True,
                column='location',
                values=[x.serialize_for_db() for x in excluded_locations],
                operator='NOT IN',
            ))
        if location_labels is not None:
            filters.append(DBMultiStringFilter(
                and_op=True,
                column='location_label',
                values=location_labels,
                operator='IN',
            ))
        if ignored_ids is not None:
            filters.append(
                DBIgnoreValuesFilter(
                    and_op=True,
                    column='identifier',
                    values=ignored_ids,
                ),
            )
        if null_columns is not None:
            filters.append(
                DBNullFilter(
                    and_op=True,
                    columns=null_columns,
                ),
            )
        if event_identifiers is not None:
            filters.append(
                DBMultiStringFilter(
                    and_op=True,
                    column='event_identifier',
                    values=event_identifiers,
                ),
            )
        if exclude_ignored_assets is True:
            if exclude_entire_event_group_on_ignored_asset is True:
                filters.append(DBIgnoredEventFilter(and_op=True))
            else:
                filters.append(DBIgnoredAssetsFilter(
                    and_op=True,
                    asset_key='asset',
                    operator='NOT IN',
                ))
        if identifiers is not None:
            filters.append(
                DBMultiIntegerFilter(
                    and_op=True,
                    column='history_events_identifier',
                    values=identifiers,
                ),
            )

        filter_query.timestamp_filter = DBTimestampFilter(
            and_op=True,
            from_ts=from_ts,
            to_ts=to_ts,
            scaling_factor=FVal(1000),  # these timestamps are in MS
        )
        filters.append(filter_query.timestamp_filter)
        filter_query.filters = filters
        return filter_query

    @staticmethod
    @abstractmethod
    def get_join_query() -> str:
        """Returns the join query needed for this particular type of history event filter"""

    @staticmethod
    @abstractmethod
    def get_columns() -> str:
        """Returns all the fields/columns of this query. There is places where just using
        * does not work due to ambiguous fields. This method helps with that."""


class HistoryEventFilterQuery(HistoryBaseEntryFilterQuery):
    """This is the event query for all types of events"""

    @staticmethod
    def get_join_query() -> str:
        return 'FROM history_events '

    @staticmethod
    def get_columns() -> str:
        return HISTORY_BASE_ENTRY_FIELDS


class EvmEventFilterQuery(HistoryBaseEntryFilterQuery):
    @classmethod
    def make(
            cls: type['EvmEventFilterQuery'],
            and_op: bool = True,
            order_by_rules: list[tuple[str, bool]] | None = None,
            limit: int | None = None,
            offset: int | None = None,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
            assets: tuple[Asset, ...] | None = None,
            event_types: list[HistoryEventType] | None = None,
            event_subtypes: list[HistoryEventSubType] | None = None,
            exclude_subtypes: list[HistoryEventSubType] | None = None,
            location: Location | None = None,
            location_labels: list[str] | None = None,
            excluded_locations: list[Location] | None = None,
            ignored_ids: list[str] | None = None,
            null_columns: list[str] | None = None,
            identifiers: list[int] | None = None,
            event_identifiers: list[str] | None = None,
            entry_types: IncludeExcludeFilterData | None = None,
            exclude_ignored_assets: bool = False,
            exclude_entire_event_group_on_ignored_asset: bool = True,
            customized_events_only: bool = False,
            tx_hashes: list[EVMTxHash] | None = None,
            counterparties: list[str] | None = None,
            products: list[EvmProduct] | None = None,
            addresses: list[ChecksumEvmAddress] | None = None,
    ) -> 'EvmEventFilterQuery':
        if entry_types is None:
            entry_type_values = [HistoryBaseEntryType.EVM_EVENT]
            entry_types = IncludeExcludeFilterData(values=entry_type_values)

        filter_query = super().make(
            and_op=and_op,
            order_by_rules=order_by_rules,
            limit=limit,
            offset=offset,
            from_ts=from_ts,
            to_ts=to_ts,
            assets=assets,
            event_types=event_types,
            event_subtypes=event_subtypes,
            exclude_subtypes=exclude_subtypes,
            location=location,
            location_labels=location_labels,
            excluded_locations=excluded_locations,
            ignored_ids=ignored_ids,
            null_columns=null_columns,
            identifiers=identifiers,
            event_identifiers=event_identifiers,
            entry_types=entry_types,
            exclude_ignored_assets=exclude_ignored_assets,
            customized_events_only=customized_events_only,
            exclude_entire_event_group_on_ignored_asset=exclude_entire_event_group_on_ignored_asset,
        )
        if counterparties is not None:
            filter_query.filters.append(DBMultiStringFilter(
                and_op=True,
                column='counterparty',
                values=counterparties,
                operator='IN',
            ))

        if products is not None:
            filter_query.filters.append(DBMultiStringFilter(
                and_op=True,
                column='product',
                values=[x.serialize() for x in products],
                operator='IN',
            ))

        if tx_hashes is not None:
            filter_query.filters.append(DBMultiBytesFilter(
                and_op=True,
                column='tx_hash',
                values=tx_hashes,
                operator='IN',
            ))

        if addresses is not None:
            filter_query.filters.append(DBMultiStringFilter(
                and_op=True,
                column='address',
                values=addresses,
                operator='IN',
            ))

        return filter_query

    @staticmethod
    def get_join_query() -> str:
        return EVM_EVENT_JOIN

    @staticmethod
    def get_columns() -> str:
        return f'{HISTORY_BASE_ENTRY_FIELDS}, {EVM_EVENT_FIELDS}'


class EthStakingEventFilterQuery(HistoryBaseEntryFilterQuery, ABC):

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_rules: list[tuple[str, bool]] | None = None,
            limit: int | None = None,
            offset: int | None = None,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
            assets: tuple[Asset, ...] | None = None,
            event_types: list[HistoryEventType] | None = None,
            event_subtypes: list[HistoryEventSubType] | None = None,
            exclude_subtypes: list[HistoryEventSubType] | None = None,
            location: Location | None = None,
            location_labels: list[str] | None = None,
            excluded_locations: list[Location] | None = None,
            ignored_ids: list[str] | None = None,
            null_columns: list[str] | None = None,
            identifiers: list[int] | None = None,
            event_identifiers: list[str] | None = None,
            entry_types: IncludeExcludeFilterData | None = None,
            exclude_ignored_assets: bool = False,
            exclude_entire_event_group_on_ignored_asset: bool = True,
            customized_events_only: bool = False,
            validator_indices: list[int] | None = None,
    ) -> Self:
        if entry_types is None:
            entry_type_values = [HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT, HistoryBaseEntryType.ETH_BLOCK_EVENT, HistoryBaseEntryType.ETH_DEPOSIT_EVENT]  # noqa: E501
            entry_types = IncludeExcludeFilterData(values=entry_type_values)

        filter_query = super().make(
            and_op=and_op,
            order_by_rules=order_by_rules,
            limit=limit,
            offset=offset,
            from_ts=from_ts,
            to_ts=to_ts,
            assets=assets,
            event_types=event_types,
            event_subtypes=event_subtypes,
            exclude_subtypes=exclude_subtypes,
            location=location,
            location_labels=location_labels,
            excluded_locations=excluded_locations,
            ignored_ids=ignored_ids,
            null_columns=null_columns,
            identifiers=identifiers,
            event_identifiers=event_identifiers,
            entry_types=entry_types,
            exclude_ignored_assets=exclude_ignored_assets,
            customized_events_only=customized_events_only,
            exclude_entire_event_group_on_ignored_asset=exclude_entire_event_group_on_ignored_asset,
        )
        if validator_indices is not None:
            filter_query.filters.append(DBMultiIntegerFilter(
                and_op=True,
                column='validator_index',
                values=validator_indices,
                operator='IN',
            ))

        return filter_query

    @staticmethod
    def get_join_query() -> str:
        return ETH_STAKING_EVENT_JOIN

    @staticmethod
    def get_columns() -> str:
        return f'{HISTORY_BASE_ENTRY_FIELDS}, {ETH_STAKING_EVENT_FIELDS}'


class WithdrawalTypesFilter(Enum):
    ALL = auto()
    ONLY_EXITS = auto()
    ONLY_PARTIAL = auto()


class EthWithdrawalFilterQuery(EthStakingEventFilterQuery):

    @classmethod
    def make(
            cls: type['EthWithdrawalFilterQuery'],
            and_op: bool = True,
            order_by_rules: list[tuple[str, bool]] | None = None,
            limit: int | None = None,
            offset: int | None = None,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
            assets: tuple[Asset, ...] | None = None,
            event_types: list[HistoryEventType] | None = None,
            event_subtypes: list[HistoryEventSubType] | None = None,
            exclude_subtypes: list[HistoryEventSubType] | None = None,
            location: Location | None = None,
            location_labels: list[str] | None = None,
            excluded_locations: list[Location] | None = None,
            ignored_ids: list[str] | None = None,
            null_columns: list[str] | None = None,
            identifiers: list[int] | None = None,
            event_identifiers: list[str] | None = None,
            entry_types: IncludeExcludeFilterData | None = None,
            exclude_ignored_assets: bool = False,
            exclude_entire_event_group_on_ignored_asset: bool = True,
            customized_events_only: bool = False,
            validator_indices: list[int] | None = None,
            withdrawal_types_filter: WithdrawalTypesFilter = WithdrawalTypesFilter.ALL,
    ) -> 'EthWithdrawalFilterQuery':
        if entry_types is None:
            entry_type_values = [HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT]
            entry_types = IncludeExcludeFilterData(values=entry_type_values)

        filter_query = super().make(
            and_op=and_op,
            order_by_rules=order_by_rules,
            limit=limit,
            offset=offset,
            from_ts=from_ts,
            to_ts=to_ts,
            assets=assets,
            event_types=event_types,
            event_subtypes=event_subtypes,
            exclude_subtypes=exclude_subtypes,
            location=location,
            location_labels=location_labels,
            excluded_locations=excluded_locations,
            ignored_ids=ignored_ids,
            null_columns=null_columns,
            identifiers=identifiers,
            event_identifiers=event_identifiers,
            entry_types=entry_types,
            exclude_ignored_assets=exclude_ignored_assets,
            exclude_entire_event_group_on_ignored_asset=exclude_entire_event_group_on_ignored_asset,
            customized_events_only=customized_events_only,
            validator_indices=validator_indices,
        )
        if withdrawal_types_filter != WithdrawalTypesFilter.ALL:
            filter_query.filters.append(DBEqualsFilter(
                and_op=True,
                column='is_exit_or_blocknumber',
                value=0 if withdrawal_types_filter == WithdrawalTypesFilter.ONLY_PARTIAL else 1,
            ))

        return filter_query

    @staticmethod
    def get_join_query() -> str:
        return ETH_STAKING_EVENT_JOIN

    @staticmethod
    def get_count_query() -> str:
        return f'SELECT COUNT(*) {ETH_STAKING_EVENT_JOIN}'


class EthBlockEventFilterQuery(EthStakingEventFilterQuery):
    pass


class EthDepositEventFilterQuery(EvmEventFilterQuery, EthStakingEventFilterQuery):
    @classmethod
    def make(  # type: ignore  # it is expected to be incompatible with supertype
            cls: type['EthDepositEventFilterQuery'],
            and_op: bool = True,
            order_by_rules: list[tuple[str, bool]] | None = None,
            limit: int | None = None,
            offset: int | None = None,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
            assets: tuple[Asset, ...] | None = None,
            event_types: list[HistoryEventType] | None = None,
            event_subtypes: list[HistoryEventSubType] | None = None,
            exclude_subtypes: list[HistoryEventSubType] | None = None,
            location: Location | None = None,
            location_labels: list[str] | None = None,
            excluded_locations: list[Location] | None = None,
            ignored_ids: list[str] | None = None,
            null_columns: list[str] | None = None,
            identifiers: list[int] | None = None,
            event_identifiers: list[str] | None = None,
            entry_types: IncludeExcludeFilterData | None = None,
            exclude_ignored_assets: bool = False,
            exclude_entire_event_group_on_ignored_asset: bool = True,
            customized_events_only: bool = False,
            tx_hashes: list[EVMTxHash] | None = None,
            validator_indices: list[int] | None = None,
    ) -> 'EthDepositEventFilterQuery':
        if entry_types is None:
            entry_type_values = [HistoryBaseEntryType.ETH_DEPOSIT_EVENT]
            entry_types = IncludeExcludeFilterData(values=entry_type_values)

        filter_query = EvmEventFilterQuery.make(
            and_op=and_op,
            order_by_rules=order_by_rules,
            limit=limit,
            offset=offset,
            from_ts=from_ts,
            to_ts=to_ts,
            assets=assets,
            event_types=event_types,
            event_subtypes=event_subtypes,
            exclude_subtypes=exclude_subtypes,
            location=location,
            location_labels=location_labels,
            excluded_locations=excluded_locations,
            ignored_ids=ignored_ids,
            null_columns=null_columns,
            identifiers=identifiers,
            event_identifiers=event_identifiers,
            entry_types=entry_types,
            exclude_ignored_assets=exclude_ignored_assets,
            tx_hashes=tx_hashes,
            customized_events_only=customized_events_only,
            exclude_entire_event_group_on_ignored_asset=exclude_entire_event_group_on_ignored_asset,
        )
        if validator_indices is not None:
            filter_query.filters.append(DBMultiIntegerFilter(
                and_op=True,
                column='validator_index',
                values=validator_indices,
                operator='IN',
            ))

        return filter_query  # type: ignore  # we are creating an EthDepositEventFilterQuery

    @staticmethod
    def get_join_query() -> str:
        return ETH_DEPOSIT_EVENT_JOIN

    @staticmethod
    def get_columns() -> str:
        return f'{HISTORY_BASE_ENTRY_FIELDS}, {EVM_EVENT_FIELDS}, {ETH_STAKING_EVENT_FIELDS}'


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBSubtableSelectFilter(DBFilter):
    """Filter that filters rows from a select of another table"""
    asset_key: str
    operator: Literal['IN', 'NOT IN']
    select_value: str
    select_table: str
    select_condition: str | None

    def prepare(self) -> tuple[list[str], list[Any]]:
        null_check = ''  # for NOT IN comparison remember NULL is a special case
        if self.operator == 'NOT IN':
            null_check = f'{self.asset_key} IS NULL OR '
        querystr = f'{null_check}{self.asset_key} {self.operator} (SELECT {self.select_value} FROM {self.select_table}'  # noqa: E501
        if self.select_condition is not None:
            querystr += f' WHERE {self.select_condition}'
        querystr += ')'
        return [querystr], []


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBIgnoredAssetsFilter(DBSubtableSelectFilter):
    """Filter that filters ignored assets"""
    select_value: str = field(default='value', init=False)
    select_table: str = field(default='multisettings', init=False)
    select_condition: str = field(default="name='ignored_asset'", init=False)


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBIgnoredEventFilter(DBFilter):
    """Filter that excludes all events with the same event_identifier if any of them has an ignored asset"""  # noqa: E501

    def prepare(self) -> tuple[list[str], list[Any]]:
        query = """
        event_identifier NOT IN (
            SELECT DISTINCT he.event_identifier
            FROM history_events he
            JOIN multisettings ms ON he.asset = ms.value
            WHERE ms.name = 'ignored_asset'
        )
        """
        return [query], []


class UserNotesFilterQuery(DBFilterQuery, FilterWithTimestamp):

    @classmethod
    def make(
            cls: type['UserNotesFilterQuery'],
            and_op: bool = True,
            order_by_rules: list[tuple[str, bool]] | None = None,
            limit: int | None = None,
            offset: int | None = None,
            from_ts: Timestamp | None = None,
            to_ts: Timestamp | None = None,
            location: str | None = None,
            substring_search: str | None = None,
    ) -> 'UserNotesFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('last_update_timestamp', True)]
        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filters: list[DBFilter] = []
        filter_query.timestamp_filter = DBTimestampFilter(
            and_op=True,
            from_ts=from_ts,
            to_ts=to_ts,
            timestamp_field='last_update_timestamp',
        )
        if substring_search is not None:
            filters.append(DBSubStringFilter(
                and_op=True,
                field='title',
                search_string=substring_search,
            ))
        if location is not None:
            filters.append(DBEqualsFilter(and_op=True, column='location', value=location))
        filters.append(filter_query.timestamp_filter)
        filter_query.filters = filters
        return filter_query


class AddressbookFilterQuery(DBFilterQuery):
    """
    Filter used to find the paginated addressbook entries using the blockchain,
    name and optional chain addresses as a filter.
    """
    @classmethod
    def make(
            cls: type['AddressbookFilterQuery'],
            and_op: bool = True,
            limit: int | None = None,
            offset: int | None = None,
            blockchain: SupportedBlockchain | None = None,
            optional_chain_addresses: list[OptionalChainAddress] | None = None,
            substring_search: str | None = None,
            order_by_rules: list[tuple[str, bool]] | None = None,
    ) -> 'AddressbookFilterQuery':
        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filters: list[DBFilter] = []
        if substring_search is not None:
            filters.append(DBSubStringFilter(
                and_op=True,
                field='name',
                search_string=substring_search,
            ))
        if blockchain is not None:
            filters.append(DBEqualsFilter(
                and_op=True,
                column='blockchain',
                value=blockchain.value,
            ))
        if optional_chain_addresses is not None:
            filters.append(DBOptionalChainAddressesFilter(
                and_op=False,
                optional_chain_addresses=optional_chain_addresses,
            ))
        filter_query.filters = filters
        return filter_query


class AssetsFilterQuery(DBFilterQuery):
    ignored_assets_handling: IgnoredAssetsHandling = IgnoredAssetsHandling.NONE

    @classmethod
    def make(
            cls: type['AssetsFilterQuery'],
            and_op: bool = True,
            order_by_rules: list[tuple[str, bool]] | None = None,
            limit: int | None = None,
            offset: int | None = None,
            name: str | None = None,
            symbol: str | None = None,
            address: ChecksumEvmAddress | None = None,
            substring_search: str | None = None,
            search_column: str | None = None,
            asset_type: AssetType | None = None,
            identifiers: list[str] | None = None,
            show_user_owned_assets_only: bool = False,
            show_whitelisted_assets_only: bool = False,
            return_exact_matches: bool = False,
            chain_id: ChainID | None = None,
            identifier_column_name: str = 'identifier',
            ignored_assets_handling: IgnoredAssetsHandling = IgnoredAssetsHandling.NONE,
    ) -> 'AssetsFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('name', True)]

        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
            order_by_case_sensitive=False,
        )
        filter_query.ignored_assets_handling = ignored_assets_handling
        filters: list[DBFilter] = []
        if name is not None:
            filters.append(DBSubStringFilter(
                and_op=True,
                field='name',
                search_string=name,
            ))
        if symbol is not None:
            filters.append(DBSubStringFilter(
                and_op=True,
                field='symbol',
                search_string=symbol,
            ))
        if asset_type is not None:
            filters.append(DBEqualsFilter(
                and_op=True,
                column='type',
                value=asset_type.serialize_for_db(),
            ))
        if substring_search is not None and search_column is not None:
            if return_exact_matches is True:
                filters.append(DBEqualsFilter(
                    and_op=True,
                    column=search_column,
                    value=substring_search,
                ))
            else:
                filters.append(DBSubStringFilter(
                    and_op=True,
                    field=search_column,
                    search_string=substring_search,
                ))
        if identifiers is not None:
            filters.append(DBMultiStringFilter(
                and_op=True,
                column=identifier_column_name,
                values=identifiers,
            ))
        if show_user_owned_assets_only is True:
            filters.append(DBSubtableSelectFilter(
                and_op=True,
                asset_key=identifier_column_name,
                operator='IN',
                select_value='asset_id',
                select_table='user_owned_assets',
                select_condition=None,
            ))
        if chain_id is not None:
            filters.append(DBEqualsFilter(
                and_op=True,
                column='chain',
                value=chain_id.serialize_for_db(),
            ))
        if address is not None:
            filters.append(DBEqualsFilter(
                and_op=True,
                column='address',
                value=address,
            ))
        if show_whitelisted_assets_only is True:
            filters.append(DBSubtableSelectFilter(
                and_op=True,
                asset_key=identifier_column_name,
                operator='IN',
                select_value='value',
                select_table='general_cache',
                select_condition=f"key='{compute_cache_key((CacheType.SPAM_ASSET_FALSE_POSITIVE,))}'",
            ))
        filter_query.filters = filters
        return filter_query


class LocationAssetMappingsFilterQuery(DBFilterQuery):
    """DBFilterQuery with a nullable DB Location filter. Here the if location_filter is None then
    no filter is applied. If location_filter exists, but with the `location` value as None then the
    filter will be applied with `location IS NULL` clause. Other normal values of location in
    location filter will work similar to DBLocationFilter."""
    location_filter: DBNullableLocationFilter | None = None

    @classmethod
    def make(
            cls: type['LocationAssetMappingsFilterQuery'],
            limit: int,
            offset: int,
            location: Location | Literal['common'] | None = None,
            location_symbol: str | None = None,
            and_op: bool = True,
    ) -> 'LocationAssetMappingsFilterQuery':
        """Make and return the LocationAssetMappingsFilterQuery instance according to the passed
        arguments. `limit` and `offset` are for pagination and works with DBFilterPagination.
        `location` can be a valid Location value, None, or "common". If `location` is None, filter
        will not be applied. If valid Location value is given, that location will be filtered. If
        `location` is "common" then filter will be applied for columns where location is NULL."""
        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
        )
        if location_symbol is not None:
            filter_query.filters.append(DBSubStringFilter(
                and_op=True,
                field='exchange_symbol',
                search_string=location_symbol,
            ))
        if location is not None:
            filter_query.location_filter = DBNullableLocationFilter(
                and_op=True,
                location=None if location == 'common' else location,
            )
            filter_query.filters.append(filter_query.location_filter)
        return filter_query


class CounterpartyAssetMappingsFilterQuery(DBFilterQuery):
    """DBFilterQuery for filtering asset mappings by counterparty data.

    counterparty: External entity that exchanges assets (e.g., "Hyperliquid").
    counterparty symbol: Identifier used by the counterparty for an asset (e.g., "HYPE").
    """
    @classmethod
    def make(
            cls: type['CounterpartyAssetMappingsFilterQuery'],
            limit: int,
            offset: int,
            counterparty: str | None = None,
            counterparty_symbol: str | None = None,
            and_op: bool = True,
    ) -> 'CounterpartyAssetMappingsFilterQuery':
        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
        )
        if counterparty_symbol is not None:
            filter_query.filters.append(DBSubStringFilter(
                and_op=True,
                field='symbol',
                search_string=counterparty_symbol,
            ))
        if counterparty is not None:
            filter_query.filters.append(DBEqualsFilter(
                and_op=True,
                column='counterparty',
                value=counterparty,
            ))

        return filter_query


class CustomAssetsFilterQuery(DBFilterQuery):
    @classmethod
    def make(
            cls: type['CustomAssetsFilterQuery'],
            order_by_rules: list[tuple[str, bool]] | None = None,
            limit: int | None = None,
            offset: int | None = None,
            identifier: str | None = None,
            name: str | None = None,
            custom_asset_type: str | None = None,
    ) -> 'CustomAssetsFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('name', True)]

        filter_query = cls.create(
            and_op=True,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filters: list[DBFilter] = []
        if identifier is not None:
            filters.append(DBEqualsFilter(
                and_op=True,
                column='identifier',
                alias='B',  # assets table.
                value=identifier,
            ))
        if name is not None:
            filters.append(DBSubStringFilter(
                and_op=True,
                field='name',
                search_string=name,
            ))
        if custom_asset_type is not None:
            filters.append(DBEqualsFilter(
                and_op=True,
                column='type',
                alias='A',  # custom_assets table
                value=custom_asset_type,
            ))
        filter_query.filters = filters
        return filter_query


class NFTFilterQuery(DBFilterQuery):
    @classmethod
    def make(
            cls: type['NFTFilterQuery'],
            order_by_rules: list[tuple[str, bool]] | None = None,
            limit: int | None = None,
            offset: int | None = None,
            owner_addresses: Sequence[ChecksumEvmAddress] | None = None,
            name: str | None = None,
            collection_name: str | None = None,
            ignored_assets_handling: IgnoredAssetsHandling = IgnoredAssetsHandling.NONE,
            lps_handling: NftLpHandling = NftLpHandling.ALL_NFTS,
            nft_id: str | None = None,
            last_price_asset: Asset | None = None,
            only_with_manual_prices: bool = False,
            with_price: bool = True,
    ) -> 'NFTFilterQuery':
        filter_query = cls.create(
            and_op=True,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filters: list[DBFilter] = []
        if owner_addresses is not None:
            filters.append(DBMultiStringFilter(
                and_op=True,
                column='owner_address',
                values=owner_addresses,
            ))
        if name is not None:
            filters.append(DBSubStringFilter(
                and_op=True,
                field='name',
                search_string=name,
            ))
        if collection_name is not None:
            filters.append(DBSubStringFilter(
                and_op=True,
                field='collection_name',
                search_string=collection_name,
            ))
        if ignored_assets_handling is not IgnoredAssetsHandling.NONE:
            filters.append(DBIgnoredAssetsFilter(
                and_op=True,
                asset_key='identifier',
                operator=ignored_assets_handling.operator(),
            ))
        if lps_handling != NftLpHandling.ALL_NFTS:
            filters.append(DBEqualsFilter(
                and_op=True,
                column='is_lp',
                value=lps_handling == NftLpHandling.ONLY_LPS,
            ))
        if nft_id is not None:
            filters.append(DBSubStringFilter(
                and_op=True,
                field='identifier',
                search_string=nft_id,
            ))
        if last_price_asset is not None:
            filters.append(DBAssetFilter(
                and_op=True,
                asset=last_price_asset,
                asset_key='last_price_asset',
            ))
        if only_with_manual_prices is True:
            filters.append(DBEqualsFilter(
                and_op=True,
                column='manual_price',
                value=1,
            ))
        if with_price is True:
            filters.append(DBNullFilter(
                and_op=True,
                verb='IS NOT',
                columns=['last_price'],
            ))

        filter_query.filters = filters
        return filter_query


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class MultiTableFilterQuery:
    """
    Filter query that allows to reuse filters for different tables structures
    (e.g. different column names).
    """
    and_op: bool
    filters: list[tuple[DBFilter, str]]  # filter + table name for which to use it.

    def prepare(self, target_table_name: str) -> tuple[str, list[Any]]:
        """Generates query and bindings for table `target_table_name`."""
        query_parts = []
        bindings: list[Any] = []
        filterstrings = []

        for (single_filter, table_name) in self.filters:
            if table_name != target_table_name:
                continue

            filters, single_bindings = single_filter.prepare()
            if len(filters) == 0:
                continue

            operator = ' AND ' if single_filter.and_op is True else ' OR '
            filterstrings.append(f'({operator.join(filters)})')
            bindings.extend(single_bindings)

        if len(filterstrings) != 0:
            operator = ' AND ' if self.and_op is True else ' OR '
            filter_query = f'WHERE {operator.join(filterstrings)}'
            query_parts.append(filter_query)

        return ' '.join(query_parts), bindings


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class LevenshteinFilterQuery(MultiTableFilterQuery):
    """
    Filter query for levenshtein search. Accepts a substring or an address to filter by and a
    chain id. Is used for querying both assets and nfts.
    """
    substring_search: str | None
    ignored_assets_handling: IgnoredAssetsHandling = IgnoredAssetsHandling.NONE

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            substring_search: str | None = None,
            chain_id: ChainID | None = None,
            address: ChecksumEvmAddress | None = None,
            ignored_assets_handling: IgnoredAssetsHandling = IgnoredAssetsHandling.NONE,
    ) -> 'LevenshteinFilterQuery':
        assert substring_search is not None or address is not None  # substring search and address can't be none at the same time  # noqa: E501
        filter_query = LevenshteinFilterQuery(
            and_op=and_op,
            filters=[],
            substring_search=substring_search,
        )
        filter_query.ignored_assets_handling = ignored_assets_handling
        filters: list[tuple[DBFilter, str]] = []  # filter + table name for which to use it.
        if substring_search is not None:
            name_filter = DBSubStringFilter(
                and_op=True,
                field='name',
                search_string=substring_search,
            )
            assets_substring_filter = DBNestedFilter(
                and_op=False,
                filters=[
                    name_filter,
                    DBSubStringFilter(
                        and_op=True,
                        field='symbol',
                        search_string=substring_search,
                    ),
                ],
            )
            filters.append((assets_substring_filter, 'assets'))
            nfts_substring_filter = DBNestedFilter(
                and_op=False,
                filters=[
                    name_filter,
                    DBSubStringFilter(
                        and_op=True,
                        field='collection_name',
                        search_string=substring_search,
                    ),
                ],
            )
            filters.append((nfts_substring_filter, 'nfts'))

        if chain_id is not None:
            nested_filter = DBNestedFilter(
                and_op=False,
                filters=[
                    DBEqualsFilter(
                        and_op=True,
                        column='chain',
                        value=chain_id.serialize_for_db(),
                        include_null_values=True,
                    ),
                    DBNullFilter(and_op=True, columns=['chain'], verb='IS'),
                ],
            )
            filters.append((nested_filter, 'assets'))

        if address is not None:
            filters.append(
                (DBEqualsFilter(and_op=True, column='address', value=address), 'assets'),
            )

        filter_query.filters = filters
        return filter_query


class TransactionsNotDecodedFilterQuery(DBFilterQuery):
    """
    Filter used to find the transactions that have not been decoded yet using chain and
    addresses as filter.

    Returns them oldest first so that decoding can happen in chronological order.
    """
    @classmethod
    def make(
            cls: type['TransactionsNotDecodedFilterQuery'],
            limit: int | None = None,
            chain_id: ChainID | None = None,
    ) -> 'TransactionsNotDecodedFilterQuery':
        filter_query = cls.create(
            and_op=True,
            limit=limit,
            offset=None,
            order_by_rules=[('C.timestamp', True)],  # order by ascending timestamp
        )
        filters: list[DBFilter] = []
        if chain_id is not None:
            filters.append(DBTransactionsPendingDecodingFilter(
                and_op=True,
                chain_id=chain_id,
            ))

        filter_query.filters = filters
        return filter_query


class AccountingRulesFilterQuery(DBFilterQuery):
    """Filter accounting rules using pagination by type, subtype and counterparty"""

    @classmethod
    def make(
            cls: type['AccountingRulesFilterQuery'],
            and_op: bool = True,
            order_by_rules: list[tuple[str, bool]] | None = None,
            limit: int | None = None,
            offset: int | None = None,
            event_types: list[HistoryEventType] | None = None,
            event_subtypes: list[HistoryEventSubType] | None = None,
            counterparties: list[str | None] | None = None,
    ) -> 'AccountingRulesFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('identifier', False)]

        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filters: list[DBFilter] = []
        if event_types is not None:
            filters.append(DBMultiStringFilter(
                and_op=True,
                column='type',
                values=[x.serialize() for x in event_types],
                operator='IN',
            ))
        if event_subtypes is not None:
            filters.append(DBMultiStringFilter(
                and_op=True,
                column='subtype',
                values=[x.serialize() for x in event_subtypes],
                operator='IN',
            ))
        if counterparties is not None:
            non_null_counterparties = []
            has_null = False
            for counterparty in counterparties:
                if counterparty is None:
                    has_null = True
                    continue
                non_null_counterparties.append(counterparty)

            if has_null:
                non_null_counterparties.append('NONE')
            if len(non_null_counterparties) != 0:
                filters.append(DBMultiStringFilter(
                    and_op=True,
                    column='counterparty',
                    values=non_null_counterparties,
                    operator='IN',
                ))

        filter_query.filters = filters
        return filter_query


class PaginatedFilterQuery(DBFilterQuery):
    """Filter for queries that only require pagination"""

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            limit: int | None = None,
            offset: int | None = None,
            order_by_rules: list[tuple[str, bool]] | None = None,
    ) -> 'PaginatedFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('identifier', False)]

        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filter_query.filters = []
        return filter_query
