import logging
from dataclasses import dataclass
from typing import Any, List, NamedTuple, Optional, Tuple, Union, cast

from typing_extensions import Literal

from rotkehlchen.accounting.ledger_actions import LedgerActionType
from rotkehlchen.accounting.structures import HistoryEventSubType, HistoryEventType
from rotkehlchen.accounting.typing import SchemaEventType
from rotkehlchen.assets.asset import Asset
from rotkehlchen.errors import DeserializationError
from rotkehlchen.logging import RotkehlchenLogsAdapter
from rotkehlchen.typing import (
    AssetMovementCategory,
    ChecksumEthAddress,
    Location,
    Timestamp,
    TradeType,
)
from rotkehlchen.utils.misc import hexstring_to_bytes, ts_now

logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)


class DBFilterOrder(NamedTuple):
    attribute: str
    ascending: bool

    def prepare(self) -> str:
        if self.attribute in ('amount', 'fee', 'rate'):
            order_by = f'CAST({self.attribute} AS REAL)'
        else:
            order_by = self.attribute

        return f'ORDER BY {order_by} {"ASC" if self.ascending else "DESC"}'


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
    timestamp_attribute: str = 'timestamp'
    from_ts: Optional[Timestamp] = None
    to_ts: Optional[Timestamp] = None

    def prepare(self) -> Tuple[List[str], List[Any]]:
        filters = []
        bindings = []
        if self.from_ts is not None:
            filters.append(f'{self.timestamp_attribute} >= ?')
            bindings.append(self.from_ts)
        if self.to_ts is not None:
            filters.append(f'{self.timestamp_attribute} <= ?')
            bindings.append(self.to_ts)

        return filters, bindings


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBETHTransactionAddressFilter(DBFilter):
    addresses: Optional[List[ChecksumEthAddress]] = None

    def prepare(self) -> Tuple[List[str], List[Any]]:
        filters = []
        bindings = []
        if self.addresses is not None:
            questionmarks = '?' * len(self.addresses)
            filters = [
                f'from_address IN ({",".join(questionmarks)})',
                f'to_address IN ({",".join(questionmarks)})',
            ]
            bindings = [*self.addresses, *self.addresses]

        return filters, bindings


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBETHTransactionHashFilter(DBFilter):
    tx_hash: Optional[Union[bytes, str]] = None

    def prepare(self) -> Tuple[List[str], List[Any]]:
        if self.tx_hash is None:
            return [], []

        if isinstance(self.tx_hash, str):
            try:
                value = hexstring_to_bytes(self.tx_hash)
            except DeserializationError as e:
                log.error(f'Failed to filter a DB transaction query by tx_hash: {str(e)}')
                return [], []
        else:
            value = self.tx_hash

        return ['tx_hash=?'], [value]


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
class DBFilterQuery():
    and_op: bool
    filters: List[DBFilter]
    order_by: Optional[DBFilterOrder] = None
    pagination: Optional[DBFilterPagination] = None

    def prepare(self, with_pagination: bool = True) -> Tuple[str, List[Any]]:
        query_parts = []
        bindings = []
        filterstrings = []

        for fil in self.filters:
            filters, single_bindings = fil.prepare()
            if len(filters) == 0:
                continue

            operator = ' AND ' if fil.and_op else ' OR '
            filterstrings.append(f'({operator.join(filters)})')
            bindings.extend(single_bindings)

        if len(filterstrings) != 0:
            operator = ' AND ' if self.and_op else ' OR '
            where_query = 'WHERE ' + operator.join(filterstrings)
            query_parts.append(where_query)

        if self.order_by is not None:
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
            order_by_attribute: Optional[str] = None,
            order_ascending: bool = True,
    ) -> 'DBFilterQuery':
        if limit is None or offset is None:
            pagination = None
        else:
            pagination = DBFilterPagination(limit=limit, offset=offset)

        if order_by_attribute is None:
            order_by = None
        else:
            order_by = DBFilterOrder(
                attribute=order_by_attribute,
                ascending=order_ascending,
            )

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
    def address_filter(self) -> Optional[DBETHTransactionAddressFilter]:
        if len(self.filters) >= 1 and isinstance(self.filters[0], DBETHTransactionAddressFilter):
            return self.filters[0]
        return None

    @property
    def addresses(self) -> Optional[List[ChecksumEthAddress]]:
        address_filter = self.address_filter
        if address_filter is None:
            return None
        return address_filter.addresses

    @addresses.setter
    def addresses(self, addresses: Optional[List[ChecksumEthAddress]]) -> None:
        address_filter = self.address_filter
        if address_filter is None:
            return
        address_filter.addresses = addresses

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_attribute: str = 'timestamp',
            order_ascending: bool = True,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            addresses: Optional[List[ChecksumEthAddress]] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            tx_hash: Optional[Union[str, bytes]] = None,
    ) -> 'ETHTransactionsFilterQuery':
        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_attribute=order_by_attribute,
            order_ascending=order_ascending,
        )
        filter_query = cast('ETHTransactionsFilterQuery', filter_query)
        filters: List[DBFilter] = []
        if tx_hash:  # tx_hash means single result so make it as single filter
            filters.append(DBETHTransactionHashFilter(and_op=False, tx_hash=tx_hash))
        else:
            filters.append(DBETHTransactionAddressFilter(and_op=False, addresses=addresses))

            filter_query.timestamp_filter = DBTimestampFilter(
                and_op=True,
                from_ts=from_ts,
                to_ts=to_ts,
                timestamp_attribute='timestamp',
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
class DBStringFilter(DBFilter):
    """Filter a column having a string value"""
    column: str
    value: str

    def prepare(self) -> Tuple[List[str], List[Any]]:
        return [f'{self.column}=?'], [self.value]


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class DBMultiStringFilter(DBFilter):
    """Filter a column having a string value out of a selection of values"""
    column: str
    values: List[str]

    def prepare(self) -> Tuple[List[str], List[Any]]:
        return (
            [f'{self.column} IN ({", ".join(["?"] * len(self.values))})'],
            self.values,
        )


class TradesFilterQuery(DBFilterQuery, FilterWithTimestamp, FilterWithLocation):

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_attribute: str = 'time',
            order_ascending: bool = True,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            base_asset: Optional[Asset] = None,
            quote_asset: Optional[Asset] = None,
            trade_type: Optional[List[TradeType]] = None,
            location: Optional[Location] = None,
    ) -> 'TradesFilterQuery':
        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_attribute=order_by_attribute,
            order_ascending=order_ascending,
        )
        filter_query = cast('TradesFilterQuery', filter_query)
        filters: List[DBFilter] = []
        if base_asset is not None:
            filters.append(DBAssetFilter(and_op=True, asset=base_asset, asset_key='base_asset'))
        if quote_asset is not None:
            filters.append(DBAssetFilter(and_op=True, asset=quote_asset, asset_key='quote_asset'))
        if trade_type is not None:
            filters.append(DBTypeFilter(and_op=True, filter_types=trade_type, type_key='type'))
        if location is not None:
            filter_query.location_filter = DBLocationFilter(and_op=True, location=location)
            filters.append(filter_query.location_filter)

        filter_query.timestamp_filter = DBTimestampFilter(
            and_op=True,
            from_ts=from_ts,
            to_ts=to_ts,
            timestamp_attribute='time',
        )
        filters.append(filter_query.timestamp_filter)
        filter_query.filters = filters
        return filter_query


class AssetMovementsFilterQuery(DBFilterQuery, FilterWithTimestamp, FilterWithLocation):

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_attribute: str = 'time',
            order_ascending: bool = True,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            asset: Optional[Asset] = None,
            action: Optional[List[AssetMovementCategory]] = None,
            location: Optional[Location] = None,
    ) -> 'AssetMovementsFilterQuery':
        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_attribute=order_by_attribute,
            order_ascending=order_ascending,
        )
        filter_query = cast('AssetMovementsFilterQuery', filter_query)
        filters: List[DBFilter] = []
        if asset is not None:
            filters.append(DBAssetFilter(and_op=True, asset=asset, asset_key='asset'))
        if action is not None:
            filters.append(DBTypeFilter(and_op=True, filter_types=action, type_key='category'))
        if location is not None:
            filter_query.location_filter = DBLocationFilter(and_op=True, location=location)
            filters.append(filter_query.location_filter)

        filter_query.timestamp_filter = DBTimestampFilter(
            and_op=True,
            from_ts=from_ts,
            to_ts=to_ts,
            timestamp_attribute='time',
        )
        filters.append(filter_query.timestamp_filter)
        filter_query.filters = filters
        return filter_query


class LedgerActionsFilterQuery(DBFilterQuery, FilterWithTimestamp, FilterWithLocation):

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_attribute: str = 'timestamp',
            order_ascending: bool = True,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            asset: Optional[Asset] = None,
            action_type: Optional[List[LedgerActionType]] = None,
            location: Optional[Location] = None,
    ) -> 'LedgerActionsFilterQuery':
        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_attribute=order_by_attribute,
            order_ascending=order_ascending,
        )
        filter_query = cast('LedgerActionsFilterQuery', filter_query)
        filters: List[DBFilter] = []
        if asset is not None:
            filters.append(DBAssetFilter(and_op=True, asset=asset, asset_key='asset'))
        if action_type is not None:
            filters.append(DBTypeFilter(and_op=True, filter_types=action_type, type_key='type'))
        if location is not None:
            filter_query.location_filter = DBLocationFilter(and_op=True, location=location)
            filters.append(filter_query.location_filter)

        filter_query.timestamp_filter = DBTimestampFilter(
            and_op=True,
            from_ts=from_ts,
            to_ts=to_ts,
            timestamp_attribute='timestamp',
        )
        filters.append(filter_query.timestamp_filter)
        filter_query.filters = filters
        return filter_query


class Eth2DailyStatsFilterQuery(DBFilterQuery, FilterWithTimestamp):

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_attribute: str = 'timestamp',
            order_ascending: bool = True,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            validators: Optional[List[int]] = None,
    ) -> 'Eth2DailyStatsFilterQuery':
        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_attribute=order_by_attribute,
            order_ascending=order_ascending,
        )
        filter_query = cast('Eth2DailyStatsFilterQuery', filter_query)
        filters: List[DBFilter] = []

        filter_query.timestamp_filter = DBTimestampFilter(
            and_op=True,
            from_ts=from_ts,
            to_ts=to_ts,
            timestamp_attribute='timestamp',
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
            order_by_attribute: str = 'timestamp',
            order_ascending: bool = True,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            report_id: Optional[int] = None,
            event_type: Optional[str] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
    ) -> 'ReportDataFilterQuery':
        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_attribute=order_by_attribute,
            order_ascending=order_ascending,
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
            timestamp_attribute='timestamp',
        )
        filters.append(filter_query.timestamp_filter)
        filter_query.filters = filters
        return filter_query


class HistoryEventFilterQuery(DBFilterQuery, FilterWithTimestamp, FilterWithLocation):

    @classmethod
    def make(
            cls,
            and_op: bool = True,
            order_by_attribute: str = 'timestamp',
            order_ascending: bool = True,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            from_ts: Optional[Timestamp] = None,
            to_ts: Optional[Timestamp] = None,
            asset: Optional[Asset] = None,
            event_type: Optional[List[HistoryEventType]] = None,
            event_subtype: Optional[List[HistoryEventSubType]] = None,
            location: Optional[Location] = None,
            location_label: Optional[str] = None,
    ) -> 'HistoryEventFilterQuery':
        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_attribute=order_by_attribute,
            order_ascending=order_ascending,
        )
        filter_query = cast('HistoryEventFilterQuery', filter_query)
        filters: List[DBFilter] = []
        if asset is not None:
            filters.append(DBAssetFilter(and_op=True, asset=asset, asset_key='asset'))
        if event_type is not None:
            filters.append(DBMultiStringFilter(
                and_op=True,
                column='type',
                values=[x.serialize() for x in event_type],
            ))
        if event_subtype is not None:
            filters.append(DBMultiStringFilter(
                and_op=True,
                column='subtype',
                values=[x.serialize() for x in event_subtype],
            ))
        if location is not None:
            filter_query.location_filter = DBLocationFilter(and_op=True, location=location)
            filters.append(filter_query.location_filter)
        if location_label is not None:
            filters.append(
                DBStringFilter(and_op=True, column='location_label', value=location_label),
            )

        filter_query.timestamp_filter = DBTimestampFilter(
            and_op=True,
            from_ts=from_ts,
            to_ts=to_ts,
            timestamp_attribute='timestamp',
        )
        filters.append(filter_query.timestamp_filter)
        filter_query.filters = filters
        return filter_query
