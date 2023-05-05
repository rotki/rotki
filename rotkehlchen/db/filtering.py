import logging
from abc import ABCMeta, abstractmethod
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from typing import Any, Generic, Literal, NamedTuple, Optional, TypeVar, Union, cast

from rotkehlchen.accounting.ledger_actions import LedgerActionType
from rotkehlchen.accounting.structures.base import HistoryBaseEntryType
from rotkehlchen.accounting.structures.evm_event import EvmProduct
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.accounting.types import SchemaEventType
from rotkehlchen.api.v1.types import IncludeExcludeFilterData
from rotkehlchen.assets.asset import Asset
from rotkehlchen.assets.types import AssetType
from rotkehlchen.chain.ethereum.modules.nft.structures import NftLpHandling
from rotkehlchen.chain.evm.types import EvmAccount
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
    SUPPORTED_CHAIN_IDS,
    AssetMovementCategory,
    ChainID,
    ChecksumEvmAddress,
    EVMTxHash,
    Location,
    Timestamp,
    TradeType,
)
from rotkehlchen.utils.misc import ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


ALL_EVENTS_DATA_JOIN = """FROM history_events
LEFT JOIN evm_events_info ON history_events.identifier=evm_events_info.identifier
LEFT JOIN eth_staking_events_info ON history_events.identifier=eth_staking_events_info.identifier """  # noqa: E501
EVM_EVENT_JOIN = 'FROM history_events INNER JOIN evm_events_info ON history_events.identifier=evm_events_info.identifier '  # noqa: E501
ETH_STAKING_EVENT_JOIN = 'FROM history_events INNER JOIN eth_staking_events_info ON history_events.identifier=eth_staking_events_info.identifier '  # noqa: E501
ETH_DEPOSIT_EVENT_JOIN = ALL_EVENTS_DATA_JOIN


T = TypeVar('T')


class DBFilterOrder(NamedTuple):
    rules: list[tuple[str, bool]]
    case_sensitive: bool

    def prepare(self) -> str:
        querystr = 'ORDER BY '
        for idx, (attribute, ascending) in enumerate(self.rules):
            if idx != 0:
                querystr += ','
            if attribute in ('amount', 'fee', 'rate'):
                order_by = f'CAST({attribute} AS REAL)'
            else:
                order_by = attribute

            if self.case_sensitive is False:
                querystr += f'{order_by} COLLATE NOCASE {"ASC" if ascending else "DESC"}'
            else:
                querystr += f'{order_by} {"ASC" if ascending else "DESC"}'

        return querystr


class DBFilterPagination(NamedTuple):
    limit: int
    offset: int

    def prepare(self) -> str:
        return f'LIMIT {self.limit} OFFSET {self.offset}'


class DBFilterGroupBy(NamedTuple):
    field_name: str

    def prepare(self) -> str:
        return f'GROUP BY {self.field_name}'


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBFilter():
    and_op: bool

    def prepare(self) -> tuple[list[str], Collection[Any]]:
        raise NotImplementedError('prepare should be implemented by subclasses')


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBNestedFilter(DBFilter):
    """Filter that allows combination of multiple subfilters with different operands."""
    and_op: bool
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

        return filterstrings, bindings


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBTimestampFilter(DBFilter):
    from_ts: Optional[Timestamp] = None
    to_ts: Optional[Timestamp] = None
    scaling_factor: Optional[FVal] = None
    timestamp_field: Optional[str] = None

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
    """ This join finds transactions involving any of the address/chain combos.
    Including internal ones. This uses the mappings we create in the DB at transaction
    addition to signify relevant addresses for a transaction.
    """
    accounts: list[EvmAccount]

    def prepare(self) -> tuple[list[str], list[Any]]:
        query_filters: list[str] = []
        bindings: list[Union[ChecksumEvmAddress, int]] = []
        query_filter_str = (
            'INNER JOIN evmtx_address_mappings WHERE '
            'evm_transactions.tx_hash=evmtx_address_mappings.tx_hash AND ('
        )
        individual_queries = []
        for address, paired_chain_id in self.accounts:
            individual_query = '(evmtx_address_mappings.address = ?'
            bindings.append(address)
            if paired_chain_id is not None:
                individual_query += ' AND evmtx_address_mappings.chain_id=?'
                bindings.append(paired_chain_id.serialize_for_db())
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
    using the query in `TRANSACTIONS_MISSING_DECODING_QUERY`. It allows filtering by addresses
    and chain.
    """
    addresses: Optional[list[ChecksumEvmAddress]]
    chain_id: Optional[ChainID]

    def prepare(self) -> tuple[list[str], list[Any]]:
        query_filters = ['B.tx_hash is NULL']
        bindings: list[Union[int, ChecksumEvmAddress]] = []
        if self.addresses is not None:
            bindings = [*self.addresses, *self.addresses]
            questionmarks = ','.join('?' * len(self.addresses))
            query_filters.append(f'(C.from_address IN ({questionmarks}) OR C.to_address IN ({questionmarks}))')  # noqa: E501
        if self.chain_id is not None:
            bindings.append(self.chain_id.serialize_for_db())
            query_filters.append('A.chain_id=?')

        query = ' AND '.join(query_filters)
        return [query], bindings


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBEvmTransactionHashFilter(DBFilter):
    tx_hash: Optional[EVMTxHash] = None

    def prepare(self) -> tuple[list[str], list[Any]]:
        if self.tx_hash is None:
            return [], []

        return ['tx_hash=?'], [self.tx_hash]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBEvmChainIDFilter(DBFilter):
    chain_id: Optional[SUPPORTED_CHAIN_IDS] = None
    table_name: Optional[str] = None

    def prepare(self) -> tuple[list[str], list[Any]]:
        if self.chain_id is None:
            return [], []

        prefix = f'{self.table_name}.' if self.table_name else ''
        return [f'{prefix}chain_id=?'], [self.chain_id.serialize_for_db()]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBReportDataReportIDFilter(DBFilter):
    report_id: Optional[Union[str, int]] = None

    def prepare(self) -> tuple[list[str], list[Any]]:
        if self.report_id is None:
            return [], []

        if isinstance(self.report_id, str):
            try:
                value = int(self.report_id)
            except DeserializationError as e:
                log.error(f'Failed to filter a DB transaction query by report_id: {str(e)}')
                return [], []
        else:
            value = self.report_id

        return ['report_id=?'], [value]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBReportDataEventTypeFilter(DBFilter):
    event_type: Optional[Union[str, SchemaEventType]] = None

    def prepare(self) -> tuple[list[str], list[Any]]:
        if self.event_type is None:
            return [], []

        if isinstance(self.event_type, str):
            try:
                value = SchemaEventType.deserialize_from_db(self.event_type)
            except DeserializationError as e:
                log.error(f'Failed to filter a DB transaction query by event_type: {str(e)}')
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
class DBSubStringFilter(DBFilter):
    field: str
    search_string: str

    def prepare(self) -> tuple[list[str], list[Any]]:
        return [f'{self.field} LIKE ?'], [f'%{self.search_string}%']


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBFilterQuery():
    and_op: bool
    filters: list[DBFilter]
    join_clause: Optional[DBFilter] = None
    group_by: Optional[DBFilterGroupBy] = None
    order_by: Optional[DBFilterOrder] = None
    pagination: Optional[DBFilterPagination] = None

    def prepare(
            self,
            with_pagination: bool = True,
            with_order: bool = True,
            with_group_by: bool = False,
    ) -> tuple[str, list[Any]]:
        query_parts = []
        bindings: list[Any] = []
        filterstrings = []

        if self.join_clause is not None:
            join_querystr, single_bindings = self.join_clause.prepare()
            query_parts.append(join_querystr[0])
            bindings.extend(single_bindings)

        for fil in self.filters:
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
            limit: Optional[int],
            offset: Optional[int],
            order_by_case_sensitive: bool = True,
            order_by_rules: Optional[list[tuple[str, bool]]] = None,
            group_by_field: Optional[str] = None,
    ) -> 'DBFilterQuery':
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


class FilterWithTimestamp():

    timestamp_filter: DBTimestampFilter

    @property
    def from_ts(self) -> Timestamp:
        if self.timestamp_filter.from_ts is None:
            return Timestamp(0)

        return self.timestamp_filter.from_ts

    @from_ts.setter
    def from_ts(self, from_ts: Optional[Timestamp]) -> None:
        self.timestamp_filter.from_ts = from_ts

    @property
    def to_ts(self) -> Timestamp:
        if self.timestamp_filter.to_ts is None:
            return ts_now()

        return self.timestamp_filter.to_ts

    @to_ts.setter
    def to_ts(self, to_ts: Optional[Timestamp]) -> None:
        self.timestamp_filter.to_ts = to_ts


class FilterWithLocation():

    location_filter: Optional[DBLocationFilter] = None

    @property
    def location(self) -> Optional[Location]:
        if self.location_filter is None:
            return None

        return self.location_filter.location


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class EvmTransactionsFilterQuery(DBFilterQuery, FilterWithTimestamp):

    @property
    def accounts(self) -> Optional[list[EvmAccount]]:
        if self.join_clause is None:
            return None

        ethaddress_filter = cast('DBEvmTransactionJoinsFilter', self.join_clause)
        return ethaddress_filter.accounts

    @property
    def chain_id(self) -> Optional[SUPPORTED_CHAIN_IDS]:
        if isinstance(self.filters[-1], DBEvmChainIDFilter):
            return self.filters[-1].chain_id
        return None

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_rules: Optional[list[tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            accounts: Optional[list[EvmAccount]] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            tx_hash: Optional[EVMTxHash] = None,
            chain_id: Optional[SUPPORTED_CHAIN_IDS] = None,
    ) -> 'EvmTransactionsFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('timestamp', True)]

        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filter_query = cast('EvmTransactionsFilterQuery', filter_query)
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
                filters.append(DBEvmChainIDFilter(and_op=True, chain_id=chain_id))

        else:
            if accounts is not None:
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
    validators: Optional[list[int]]

    def prepare(self) -> tuple[list[str], list[Any]]:
        if self.validators is None:
            return [], []
        questionmarks = '?' * len(self.validators)
        return [f'validator_index IN ({",".join(questionmarks)})'], self.validators


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBTypeFilter(DBFilter):
    """A filter for type/category/HistoryBaseEntry enums"""
    filter_types: Union[
        list[TradeType],
        list[AssetMovementCategory],
        list[LedgerActionType],
    ]
    type_key: Literal['type', 'subtype', 'category']

    def prepare(self) -> tuple[list[str], list[Any]]:
        if len(self.filter_types) == 1:
            return [f'{self.type_key}=?'], [self.filter_types[0].serialize_for_db()]
        return (
            [f'{self.type_key} IN ({", ".join(["?"] * len(self.filter_types))})'],
            [entry.serialize_for_db() for entry in self.filter_types],
        )


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBEqualsFilter(DBFilter):
    """Filter a column by comparing its column to its value for equality."""
    column: str
    value: Union[str, bytes, int, bool]
    alias: Optional[str] = None

    def prepare(self) -> tuple[list[str], list[Any]]:
        key_name = self.column
        if self.alias is not None:
            key_name = f'{self.alias}.{key_name}'
        return [f'{key_name}=?'], [self.value]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBMultiValueFilter(Generic[T], DBFilter):
    """Filter a column having a value out of a selection of values"""
    column: str
    values: list[T]
    operator: Literal['IN', 'NOT IN'] = 'IN'

    def prepare(self) -> tuple[list[str], list[T]]:
        suffix = ''  # for NOT IN comparison remember NULL is a special case
        if self.operator == 'NOT IN':
            suffix = f' OR {self.column} IS NULL'
        return (
            [f'{self.column} {self.operator} ({", ".join(["?"] * len(self.values))}){suffix}'],
            self.values,
        )


class DBMultiStringFilter(DBMultiValueFilter[str]):
    """Filter a column having a string value out of a selection of values"""


class DBMultiBytesFilter(DBMultiValueFilter[bytes]):
    """Filter a column having a bytes value out of a selection of values"""


class DBMultiIntegerFilter(DBMultiValueFilter[int]):
    """Filter a column having an integer value out of a selection of values"""


class TradesFilterQuery(DBFilterQuery, FilterWithTimestamp, FilterWithLocation):

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_rules: Optional[list[tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            base_assets: Optional[tuple[Asset, ...]] = None,
            quote_assets: Optional[tuple[Asset, ...]] = None,
            trade_type: Optional[list[TradeType]] = None,
            location: Optional[Location] = None,
            trades_idx_to_ignore: Optional[set[str]] = None,
    ) -> 'TradesFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('timestamp', True)]

        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filter_query = cast('TradesFilterQuery', filter_query)
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

        filter_query.timestamp_filter = DBTimestampFilter(
            and_op=True,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        filters.append(filter_query.timestamp_filter)
        filter_query.filters = filters
        return filter_query


class AssetMovementsFilterQuery(DBFilterQuery, FilterWithTimestamp, FilterWithLocation):

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_rules: Optional[list[tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            assets: Optional[tuple[Asset, ...]] = None,
            action: Optional[list[AssetMovementCategory]] = None,
            location: Optional[Location] = None,
    ) -> 'AssetMovementsFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('timestamp', True)]

        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filter_query = cast('AssetMovementsFilterQuery', filter_query)
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
        if action is not None:
            filters.append(DBTypeFilter(and_op=True, filter_types=action, type_key='category'))
        if location is not None:
            filter_query.location_filter = DBLocationFilter(and_op=True, location=location)
            filters.append(filter_query.location_filter)

        filter_query.timestamp_filter = DBTimestampFilter(
            and_op=True,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        filters.append(filter_query.timestamp_filter)
        filter_query.filters = filters
        return filter_query


class LedgerActionsFilterQuery(DBFilterQuery, FilterWithTimestamp, FilterWithLocation):

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_rules: Optional[list[tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            assets: Optional[tuple[Asset, ...]] = None,
            action_type: Optional[list[LedgerActionType]] = None,
            location: Optional[Location] = None,
    ) -> 'LedgerActionsFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('timestamp', True)]
        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filter_query = cast('LedgerActionsFilterQuery', filter_query)
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
        if action_type is not None:
            filters.append(DBTypeFilter(and_op=True, filter_types=action_type, type_key='type'))
        if location is not None:
            filter_query.location_filter = DBLocationFilter(and_op=True, location=location)
            filters.append(filter_query.location_filter)

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
            cls,
            and_op: bool = True,
            order_by_rules: Optional[list[tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            validators: Optional[list[int]] = None,
    ) -> 'Eth2DailyStatsFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('timestamp', True)]

        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filter_query = cast('Eth2DailyStatsFilterQuery', filter_query)
        filters: list[DBFilter] = []

        filter_query.timestamp_filter = DBTimestampFilter(
            and_op=True,
            from_ts=from_ts,
            to_ts=to_ts,
        )
        filters.append(filter_query.timestamp_filter)
        filters.append(DBEth2ValidatorIndicesFilter(and_op=True, validators=validators))
        filter_query.filters = filters
        return filter_query


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class ReportDataFilterQuery(DBFilterQuery, FilterWithTimestamp):

    @property
    def report_id_filter(self) -> Optional[DBReportDataReportIDFilter]:
        if len(self.filters) >= 1 and isinstance(self.filters[0], DBReportDataReportIDFilter):
            return self.filters[0]
        return None

    @property
    def event_type_filter(self) -> Optional[DBReportDataEventTypeFilter]:
        if len(self.filters) >= 2 and isinstance(self.filters[1], DBReportDataEventTypeFilter):
            return self.filters[1]
        return None

    @property
    def report_id(self) -> Optional[Union[str, int]]:
        report_id_filter = self.report_id_filter
        if report_id_filter is None:
            return None
        return report_id_filter.report_id

    @property
    def event_type(self) -> Optional[Union[str, SchemaEventType]]:
        event_type_filter = self.event_type_filter
        if event_type_filter is None:
            return None
        return event_type_filter.event_type

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_rules: Optional[list[tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            report_id: Optional[int] = None,
            event_type: Optional[str] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
    ) -> 'ReportDataFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('timestamp', True)]

        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filter_query = cast('ReportDataFilterQuery', filter_query)
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
        null_columns = []
        for column in self.columns:
            null_columns.append(f'{column} {self.verb} NULL')
        return null_columns, []


T_HistoryFilterQuery = TypeVar('T_HistoryFilterQuery', bound='HistoryBaseEntryFilterQuery')


class HistoryBaseEntryFilterQuery(DBFilterQuery, FilterWithTimestamp, FilterWithLocation, metaclass=ABCMeta):  # noqa: E501

    @classmethod
    def make(
            cls: type[T_HistoryFilterQuery],
            and_op: bool = True,
            order_by_rules: Optional[list[tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            assets: Optional[tuple[Asset, ...]] = None,
            event_types: Optional[list[HistoryEventType]] = None,
            event_subtypes: Optional[list[HistoryEventSubType]] = None,
            exclude_subtypes: Optional[list[HistoryEventSubType]] = None,
            location: Optional[Location] = None,
            location_labels: Optional[list[str]] = None,
            ignored_ids: Optional[list[str]] = None,
            null_columns: Optional[list[str]] = None,
            event_identifiers: Optional[list[str]] = None,
            entry_types: Optional[IncludeExcludeFilterData] = None,
            exclude_ignored_assets: bool = False,
    ) -> T_HistoryFilterQuery:
        if order_by_rules is None:
            order_by_rules = [('timestamp', True), ('sequence_index', True)]

        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
            group_by_field='event_identifier',
        )
        filter_query = cast(T_HistoryFilterQuery, filter_query)
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
            values = entry_types.values
            behaviour = entry_types.behaviour
            filters.append(DBMultiIntegerFilter(
                and_op=True,
                column='entry_type',
                values=[x.value for x in values],
                operator=behaviour,
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
            filters.append(DBIgnoredAssetsFilter(and_op=True, asset_key='asset'))

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
    def get_count_query() -> str:
        """Returns the count query needed for this particular type of history event filter"""


class HistoryEventFilterQuery(HistoryBaseEntryFilterQuery):
    """This is the event query for all types of events"""

    @staticmethod
    def get_join_query() -> str:
        return 'FROM history_events '

    @staticmethod
    def get_count_query() -> str:
        return 'SELECT COUNT(*) FROM history_events '


class EvmEventFilterQuery(HistoryBaseEntryFilterQuery):
    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_rules: Optional[list[tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            assets: Optional[tuple[Asset, ...]] = None,
            event_types: Optional[list[HistoryEventType]] = None,
            event_subtypes: Optional[list[HistoryEventSubType]] = None,
            exclude_subtypes: Optional[list[HistoryEventSubType]] = None,
            location: Optional[Location] = None,
            location_labels: Optional[list[str]] = None,
            ignored_ids: Optional[list[str]] = None,
            null_columns: Optional[list[str]] = None,
            event_identifiers: Optional[list[str]] = None,
            entry_types: Optional[IncludeExcludeFilterData] = None,
            exclude_ignored_assets: bool = False,
            tx_hashes: Optional[list[EVMTxHash]] = None,
            counterparties: Optional[list[str]] = None,
            products: Optional[list[EvmProduct]] = None,
    ) -> 'EvmEventFilterQuery':
        if entry_types is None:
            entry_type_values = [HistoryBaseEntryType.EVM_EVENT]
            entry_types = IncludeExcludeFilterData(values=entry_type_values, behaviour='IN')

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
            ignored_ids=ignored_ids,
            null_columns=null_columns,
            event_identifiers=event_identifiers,
            entry_types=entry_types,
            exclude_ignored_assets=exclude_ignored_assets,
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
                values=tx_hashes,  # type: ignore  # EVMTxHash is equal to bytes
                operator='IN',
            ))

        return filter_query

    @staticmethod
    def get_join_query() -> str:
        return EVM_EVENT_JOIN

    @staticmethod
    def get_count_query() -> str:
        return f'SELECT COUNT(*) {EVM_EVENT_JOIN}'


class EthStakingEventFilterQuery(HistoryBaseEntryFilterQuery):

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_rules: Optional[list[tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            assets: Optional[tuple[Asset, ...]] = None,
            event_types: Optional[list[HistoryEventType]] = None,
            event_subtypes: Optional[list[HistoryEventSubType]] = None,
            exclude_subtypes: Optional[list[HistoryEventSubType]] = None,
            location: Optional[Location] = None,
            location_labels: Optional[list[str]] = None,
            ignored_ids: Optional[list[str]] = None,
            null_columns: Optional[list[str]] = None,
            event_identifiers: Optional[list[str]] = None,
            entry_types: Optional[IncludeExcludeFilterData] = None,
            exclude_ignored_assets: bool = False,
            validator_indices: Optional[list[int]] = None,
    ) -> 'EthStakingEventFilterQuery':
        if entry_types is None:
            entry_type_values = [HistoryBaseEntryType.ETH_WITHDRAWAL_EVENT, HistoryBaseEntryType.ETH_BLOCK_EVENT, HistoryBaseEntryType.ETH_DEPOSIT_EVENT]  # noqa: E501
            entry_types = IncludeExcludeFilterData(values=entry_type_values, behaviour='IN')

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
            ignored_ids=ignored_ids,
            null_columns=null_columns,
            event_identifiers=event_identifiers,
            entry_types=entry_types,
            exclude_ignored_assets=exclude_ignored_assets,
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
    def get_count_query() -> str:
        return f'SELECT COUNT(*) {ETH_STAKING_EVENT_JOIN}'


class EthWithdrawalFilterQuery(EthStakingEventFilterQuery):
    pass


class EthBlockEventFilterQuery(EthStakingEventFilterQuery):
    pass


class EthDepositEventFilterQuery(EvmEventFilterQuery, EthStakingEventFilterQuery):
    @classmethod
    def make(  # type: ignore  # it is expected to be incompatible with supertype
            cls,
            and_op: bool = True,
            order_by_rules: Optional[list[tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            assets: Optional[tuple[Asset, ...]] = None,
            event_types: Optional[list[HistoryEventType]] = None,
            event_subtypes: Optional[list[HistoryEventSubType]] = None,
            exclude_subtypes: Optional[list[HistoryEventSubType]] = None,
            location: Optional[Location] = None,
            location_labels: Optional[list[str]] = None,
            ignored_ids: Optional[list[str]] = None,
            null_columns: Optional[list[str]] = None,
            event_identifiers: Optional[list[str]] = None,
            entry_types: Optional[IncludeExcludeFilterData] = None,
            exclude_ignored_assets: bool = False,
            tx_hashes: Optional[list[EVMTxHash]] = None,
            validator_indices: Optional[list[int]] = None,
    ) -> 'EthDepositEventFilterQuery':
        if entry_types is None:
            entry_type_values = [HistoryBaseEntryType.ETH_DEPOSIT_EVENT]
            entry_types = IncludeExcludeFilterData(values=entry_type_values, behaviour='IN')

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
            ignored_ids=ignored_ids,
            null_columns=null_columns,
            event_identifiers=event_identifiers,
            entry_types=entry_types,
            exclude_ignored_assets=exclude_ignored_assets,
            tx_hashes=tx_hashes,
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
    def get_count_query() -> str:
        return f'SELECT COUNT(*) {ETH_DEPOSIT_EVENT_JOIN}'


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBIgnoredAssetsFilter(DBFilter):
    """Filter that removes rows with ignored assets"""
    asset_key: str

    def prepare(self) -> tuple[list[str], list[Any]]:
        filters = [f'{self.asset_key} IS NULL OR {self.asset_key} NOT IN (SELECT value FROM multisettings WHERE name="ignored_asset")']  # noqa: E501
        return filters, []


class UserNotesFilterQuery(DBFilterQuery, FilterWithTimestamp):

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_rules: Optional[list[tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            location: Optional[str] = None,
            substring_search: Optional[str] = None,
    ) -> 'UserNotesFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('last_update_timestamp', True)]
        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filter_query = cast('UserNotesFilterQuery', filter_query)
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


class AssetsFilterQuery(DBFilterQuery):
    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_rules: Optional[list[tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            name: Optional[str] = None,
            symbol: Optional[str] = None,
            address: Optional[ChecksumEvmAddress] = None,
            substring_search: Optional[str] = None,
            search_column: Optional[str] = None,
            asset_type: Optional[AssetType] = None,
            identifiers: Optional[list[str]] = None,
            return_exact_matches: bool = False,
            chain_id: Optional[ChainID] = None,
            identifier_column_name: str = 'identifier',
            ignored_assets_filter_params: Optional[tuple[Literal['IN', 'NOT IN'], Iterable[str]]] = None,  # noqa: E501
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
        filter_query = cast('AssetsFilterQuery', filter_query)

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
        if ignored_assets_filter_params is not None:
            filters.append(DBMultiStringFilter(
                and_op=True,
                column=identifier_column_name,
                operator=ignored_assets_filter_params[0],
                values=list(ignored_assets_filter_params[1]),
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
        filter_query.filters = filters
        return filter_query


class CustomAssetsFilterQuery(DBFilterQuery):
    @classmethod
    def make(
            cls,
            order_by_rules: Optional[list[tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            identifier: Optional[str] = None,
            name: Optional[str] = None,
            custom_asset_type: Optional[str] = None,
    ) -> 'CustomAssetsFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('name', True)]

        filter_query = cls.create(
            and_op=True,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filter_query = cast('CustomAssetsFilterQuery', filter_query)

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
            cls,
            order_by_rules: Optional[list[tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            owner_addresses: Optional[list[str]] = None,
            name: Optional[str] = None,
            collection_name: Optional[str] = None,
            ignored_assets_filter_params: Optional[tuple[Literal['IN', 'NOT IN'], Iterable[str]]] = None,  # noqa: E501
            lps_handling: NftLpHandling = NftLpHandling.ALL_NFTS,
            nft_id: Optional[str] = None,
            last_price_asset: Optional[Asset] = None,
            only_with_manual_prices: bool = False,
            with_price: bool = True,
    ) -> 'NFTFilterQuery':
        filter_query = cls.create(
            and_op=True,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filter_query = cast('NFTFilterQuery', filter_query)
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
        if ignored_assets_filter_params is not None:
            filters.append(DBMultiStringFilter(
                and_op=True,
                column='identifier',
                operator=ignored_assets_filter_params[0],
                values=list(ignored_assets_filter_params[1]),
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
class MultiTableFilterQuery():
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
    Filter query for levenshtein search. Accepts a substring to filter by and a chain id.
    Is used for querying both assets and nfts.
    """
    substring_search: str

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            substring_search: str = '',  # substring is always required for levenstein
            chain_id: Optional[ChainID] = None,
            ignored_assets_filter_params: Optional[tuple[Literal['IN', 'NOT IN'], Iterable[str]]] = None,  # noqa: E501
    ) -> 'LevenshteinFilterQuery':
        filter_query = LevenshteinFilterQuery(
            and_op=and_op,
            filters=[],
            substring_search=substring_search,
        )
        filters: list[tuple[DBFilter, str]] = []  # filter + table name for which to use it.

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
            new_filter = DBEqualsFilter(
                and_op=True,
                column='chain',
                value=chain_id.serialize_for_db(),
            )
            filters.append((new_filter, 'assets'))

        if ignored_assets_filter_params is not None:
            ignored_assets_filter = DBMultiStringFilter(
                and_op=True,
                column='assets.identifier',
                operator=ignored_assets_filter_params[0],
                values=list(ignored_assets_filter_params[1]),
            )
            filters.append((ignored_assets_filter, 'assets'))

        filter_query.filters = filters
        return filter_query


class TransactionsNotDecodedFilterQuery(DBFilterQuery):
    """
    Filter used to find the transactions that have not been decoded yet using chain and
    addresses as filter.
    """
    @classmethod
    def make(
            cls,
            limit: Optional[int] = None,
            addresses: Optional[list[ChecksumEvmAddress]] = None,
            chain_id: Optional[ChainID] = None,
    ) -> 'TransactionsNotDecodedFilterQuery':
        filter_query = cls.create(
            and_op=True,
            limit=limit,
            offset=None,
            order_by_rules=None,
        )
        filter_query = cast('TransactionsNotDecodedFilterQuery', filter_query)

        filters: list[DBFilter] = []
        if addresses is not None or chain_id is not None:
            filters.append(DBTransactionsPendingDecodingFilter(
                and_op=True,
                addresses=addresses,
                chain_id=chain_id,
            ))

        filter_query.filters = filters
        return filter_query
