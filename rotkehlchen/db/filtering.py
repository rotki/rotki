import logging
from dataclasses import dataclass
from typing import Any, Generic, List, Literal, NamedTuple, Optional, Tuple, TypeVar, Union, cast

from rotkehlchen.accounting.ledger_actions import LedgerActionType
from rotkehlchen.accounting.structures.types import HistoryEventSubType, HistoryEventType
from rotkehlchen.accounting.types import SchemaEventType
from rotkehlchen.assets.asset import Asset, EvmToken
from rotkehlchen.assets.types import AssetType
from rotkehlchen.errors.serialization import DeserializationError
from rotkehlchen.fval import FVal
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.types import (
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

T = TypeVar('T')


class DBFilterOrder(NamedTuple):
    rules: List[Tuple[str, bool]]
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


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBFilter():
    and_op: bool

    def prepare(self) -> Tuple[List[str], List[Any]]:
        raise NotImplementedError('prepare should be implemented by subclasses')


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBTimestampFilter(DBFilter):
    from_ts: Optional[Timestamp] = None
    to_ts: Optional[Timestamp] = None
    scaling_factor: Optional[FVal] = None
    timestamp_field: Optional[str] = None

    def prepare(self) -> Tuple[List[str], List[Any]]:
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
class DBETHTransactionJoinsFilter(DBFilter):
    """ This join filter does 2 things:

    1. If addresses is not None or empty, find transactions involving any of the addresses.
    Including in an internal. This uses the mappings we create in the DB at transaction
    addition to signify relevant addresses for a transaction.

    2. If join_events is True, join history_events which makes it possible to apply
    filters by history_events' properties
    """
    addresses: Optional[List[ChecksumEvmAddress]]
    should_join_events: bool = False

    def prepare(self) -> Tuple[List[str], List[Any]]:
        query_filters, bindings = [], []
        if self.should_join_events is True:
            query_filters.append(
                'LEFT JOIN (SELECT event_identifier, counterparty, asset FROM history_events) '
                'ON ethereum_transactions.tx_hash=event_identifier',
            )
        if self.addresses is not None:
            questionmarks = '?' * len(self.addresses)
            query_filters.append(
                f'INNER JOIN ethtx_address_mappings WHERE '
                f'ethereum_transactions.tx_hash=ethtx_address_mappings.tx_hash AND '
                f'ethtx_address_mappings.address IN ({",".join(questionmarks)})',
            )
            bindings += self.addresses
        else:
            # We need this because other filters expect the join clause to end with a WHERE clause.
            query_filters.append('WHERE 1')

        query = f' {" ".join(query_filters)} '
        return [query], bindings


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBETHTransactionHashFilter(DBFilter):
    tx_hash: Optional[EVMTxHash] = None

    def prepare(self) -> Tuple[List[str], List[Any]]:
        if self.tx_hash is None:
            return [], []

        return ['tx_hash=?'], [self.tx_hash]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBReportDataReportIDFilter(DBFilter):
    report_id: Optional[Union[str, int]] = None

    def prepare(self) -> Tuple[List[str], List[Any]]:
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

    def prepare(self) -> Tuple[List[str], List[Any]]:
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

    def prepare(self) -> Tuple[List[str], List[Any]]:
        return ['location=?'], [self.location.serialize_for_db()]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBSubStringFilter(DBFilter):
    field: str
    search_string: str

    def prepare(self) -> Tuple[List[str], List[Any]]:
        return [f'{self.field} LIKE ?'], [f'%{self.search_string}%']


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBFilterQuery():
    and_op: bool
    filters: List[DBFilter]
    join_clause: Optional[DBFilter] = None
    order_by: Optional[DBFilterOrder] = None
    pagination: Optional[DBFilterPagination] = None

    def prepare(
            self,
            with_pagination: bool = True,
            with_order: bool = True,
    ) -> Tuple[str, List[Any]]:
        query_parts = []
        bindings = []
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
            order_by_rules: Optional[List[Tuple[str, bool]]] = None,
    ) -> 'DBFilterQuery':
        if limit is None or offset is None:
            pagination = None
        else:
            pagination = DBFilterPagination(limit=limit, offset=offset)

        if order_by_rules is None:
            order_by = None
        else:
            order_by = DBFilterOrder(rules=order_by_rules, case_sensitive=order_by_case_sensitive)

        return cls(
            and_op=and_op,
            filters=[],
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
class ETHTransactionsFilterQuery(DBFilterQuery, FilterWithTimestamp):

    @property
    def addresses(self) -> Optional[List[ChecksumEvmAddress]]:
        if self.join_clause is None:
            return None

        ethaddress_filter = cast('DBETHTransactionJoinsFilter', self.join_clause)
        return ethaddress_filter.addresses

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_rules: Optional[List[Tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            addresses: Optional[List[ChecksumEvmAddress]] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            tx_hash: Optional[EVMTxHash] = None,
            protocols: Optional[List[str]] = None,
            asset: Optional[EvmToken] = None,
            exclude_ignored_assets: bool = False,
    ) -> 'ETHTransactionsFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('timestamp', True)]

        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filter_query = cast('ETHTransactionsFilterQuery', filter_query)
        filters: List[DBFilter] = []
        if tx_hash is not None:  # tx_hash means single result so make it as single filter
            filters.append(DBETHTransactionHashFilter(and_op=False, tx_hash=tx_hash))
        else:
            should_join_events = asset is not None or protocols is not None or exclude_ignored_assets is True  # noqa: E501
            if addresses is not None or should_join_events is True:
                filter_query.join_clause = DBETHTransactionJoinsFilter(
                    and_op=False,
                    addresses=addresses,
                    should_join_events=should_join_events,
                )

            if asset is not None:
                filters.append(DBAssetFilter(and_op=True, asset=asset, asset_key='asset'))
            if protocols is not None:
                filters.append(DBProtocolsFilter(and_op=True, protocols=protocols))
            if exclude_ignored_assets is True:
                filters.append(DBIgnoredAssetsFilter(and_op=True, asset_key='asset'))

            filter_query.timestamp_filter = DBTimestampFilter(
                and_op=True,
                from_ts=from_ts,
                to_ts=to_ts,
            )
            filters.append(filter_query.timestamp_filter)

        filter_query.filters = filters
        return filter_query


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBAssetFilter(DBFilter):
    asset: Asset
    asset_key: str

    def prepare(self) -> Tuple[List[str], List[Any]]:
        return [f'{self.asset_key}=?'], [self.asset.identifier]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBIgnoreValuesFilter(DBFilter):
    column: str
    values: List[Any]

    def prepare(self) -> Tuple[List[str], List[Any]]:
        if len(self.values) == 0:
            return [], []
        return [f'{self.column} NOT IN ({", ".join(["?"] * len(self.values))})'], self.values


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBEth2ValidatorIndicesFilter(DBFilter):
    """A filter for Eth2 validator indices"""
    validators: Optional[List[int]]

    def prepare(self) -> Tuple[List[str], List[Any]]:
        if self.validators is None:
            return [], []
        questionmarks = '?' * len(self.validators)
        return [f'validator_index IN ({",".join(questionmarks)})'], self.validators


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBTypeFilter(DBFilter):
    """A filter for type/category/HistoryBaseEntry enums"""
    filter_types: Union[
        List[TradeType],
        List[AssetMovementCategory],
        List[LedgerActionType],
    ]
    type_key: Literal['type', 'subtype', 'category']

    def prepare(self) -> Tuple[List[str], List[Any]]:
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
    value: Union[str, bytes, int]
    alias: Optional[str] = None

    def prepare(self) -> Tuple[List[str], List[Any]]:
        key_name = self.column
        if self.alias is not None:
            key_name = f'{self.alias}.{key_name}'
        return [f'{key_name}=?'], [self.value]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBMultiValueFilter(Generic[T], DBFilter):
    """Filter a column having a string value out of a selection of values"""
    column: str
    values: List[T]
    operator: Literal['IN', 'NOT IN'] = 'IN'

    def prepare(self) -> Tuple[List[str], List[T]]:
        return (
            [f'{self.column} {self.operator} ({", ".join(["?"] * len(self.values))}) OR {self.column} IS NULL'],  # noqa: E501
            self.values,
        )


class DBMultiStringFilter(DBMultiValueFilter[str]):
    """Filter a column having a string value out of a selection of values"""
    ...


class DBMultiBytesFilter(DBMultiValueFilter[bytes]):
    """Filter a column having a bytes value out of a selection of values"""
    ...


class TradesFilterQuery(DBFilterQuery, FilterWithTimestamp, FilterWithLocation):

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_rules: Optional[List[Tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            base_assets: Optional[Tuple[Asset, ...]] = None,
            quote_assets: Optional[Tuple[Asset, ...]] = None,
            trade_type: Optional[List[TradeType]] = None,
            location: Optional[Location] = None,
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
        filters: List[DBFilter] = []
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
            order_by_rules: Optional[List[Tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            assets: Optional[Tuple[Asset, ...]] = None,
            action: Optional[List[AssetMovementCategory]] = None,
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
        filters: List[DBFilter] = []
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
            order_by_rules: Optional[List[Tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            assets: Optional[Tuple[Asset, ...]] = None,
            action_type: Optional[List[LedgerActionType]] = None,
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
        filters: List[DBFilter] = []
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
            order_by_rules: Optional[List[Tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            validators: Optional[List[int]] = None,
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
        filters: List[DBFilter] = []

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
            order_by_rules: Optional[List[Tuple[str, bool]]] = None,
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
        filters: List[DBFilter] = []
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
    columns: List[str]

    def prepare(self) -> Tuple[List[str], List[Any]]:
        null_columns = []
        for column in self.columns:
            null_columns.append(f'{column} IS NULL')
        return null_columns, []


class HistoryEventFilterQuery(DBFilterQuery, FilterWithTimestamp, FilterWithLocation):

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_rules: Optional[List[Tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            assets: Optional[Tuple[Asset, ...]] = None,
            event_types: Optional[List[HistoryEventType]] = None,
            event_subtypes: Optional[List[HistoryEventSubType]] = None,
            exclude_subtypes: Optional[List[HistoryEventSubType]] = None,
            location: Optional[Location] = None,
            location_label: Optional[str] = None,
            ignored_ids: Optional[List[str]] = None,
            null_columns: Optional[List[str]] = None,
            event_identifiers: Optional[List[bytes]] = None,
            protocols: Optional[List[str]] = None,
            exclude_ignored_assets: bool = False,
    ) -> 'HistoryEventFilterQuery':
        if order_by_rules is None:
            order_by_rules = [('timestamp', True), ('sequence_index', True)]

        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_rules=order_by_rules,
        )
        filter_query = cast('HistoryEventFilterQuery', filter_query)
        filters: List[DBFilter] = []
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
        if event_types is not None:
            filters.append(DBMultiStringFilter(
                and_op=True,
                column='type',
                values=[x.serialize() for x in event_types],
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
        if location_label is not None:
            filters.append(
                DBEqualsFilter(and_op=True, column='location_label', value=location_label),
            )
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
                DBMultiBytesFilter(
                    and_op=True,
                    column='event_identifier',
                    values=event_identifiers,
                ),
            )
        if protocols is not None:
            filters.append(
                DBProtocolsFilter(and_op=True, protocols=protocols),
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


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBProtocolsFilter(DBFilter):
    """Protocols should be not empty. Otherwise, it can break the query's logic"""
    protocols: List[str]

    def prepare(self) -> Tuple[List[str], List[Any]]:
        questionmarks = ','.join('?' * len(self.protocols))
        filters = [f'counterparty IN ({questionmarks})']
        bindings = self.protocols
        return filters, bindings


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBIgnoredAssetsFilter(DBFilter):
    """Filter that removes rows with ignored assets"""
    asset_key: str

    def prepare(self) -> Tuple[List[str], List[Any]]:
        filters = [f'{self.asset_key} IS NULL OR {self.asset_key} NOT IN (SELECT value FROM multisettings WHERE name="ignored_asset")']  # noqa: E501
        return filters, []


class UserNotesFilterQuery(DBFilterQuery, FilterWithTimestamp):

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_rules: Optional[List[Tuple[str, bool]]] = None,
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
        filters: List[DBFilter] = []
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
            order_by_rules: Optional[List[Tuple[str, bool]]] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            name: Optional[str] = None,
            symbol: Optional[str] = None,
            substring_search: Optional[str] = None,
            search_column: Optional[str] = None,
            asset_type: Optional[AssetType] = None,
            identifiers: Optional[List[str]] = None,
            return_exact_matches: bool = False,
            evm_chain: Optional[ChainID] = None,
            ignored_assets_filter_params: Optional[Tuple[Literal['IN', 'NOT IN'], List[str]]] = None,  # noqa: E501
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

        filters: List[DBFilter] = []
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
                column='identifier',
                values=identifiers,
            ))
        if ignored_assets_filter_params is not None:
            filters.append(DBMultiStringFilter(
                and_op=True,
                column='identifier',
                operator=ignored_assets_filter_params[0],
                values=ignored_assets_filter_params[1],
            ))
        if evm_chain is not None:
            filters.append(DBEqualsFilter(
                and_op=True,
                column='chain',
                value=evm_chain.serialize_for_db(),
            ))
        filter_query.filters = filters
        return filter_query


class CustomAssetsFilterQuery(DBFilterQuery):
    @classmethod
    def make(
            cls,
            order_by_rules: Optional[List[Tuple[str, bool]]] = None,
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

        filters: List[DBFilter] = []
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
