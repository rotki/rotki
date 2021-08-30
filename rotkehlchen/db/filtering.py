from dataclasses import dataclass
from typing import Any, List, NamedTuple, Optional, Tuple, cast

from rotkehlchen.typing import ChecksumEthAddress, Timestamp


class DBFilterOrder(NamedTuple):
    attribute: str
    ascending: bool

    def prepare(self) -> str:
        return f'ORDER BY {self.attribute} {"ASC" if self.ascending else "DESC"}'


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
class DBFilterQuery():
    and_op: bool
    filters: List[DBFilter]
    order_by: Optional[DBFilterOrder] = None
    pagination: Optional[DBFilterPagination] = None

    def prepare(self) -> Tuple[str, List[Any]]:
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

        if self.pagination is not None:
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
        # if None in (limit, offset):
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


@dataclass(init=True, repr=True, eq=True, order=False, unsafe_hash=False, frozen=False)
class ETHTransactionsFilterQuery(DBFilterQuery):

    @property
    def address_filter(self) -> DBETHTransactionAddressFilter:
        assert len(self.filters) == 2
        assert isinstance(self.filters[0], DBETHTransactionAddressFilter)
        return self.filters[0]

    @property
    def timestamp_filter(self) -> DBTimestampFilter:
        assert len(self.filters) == 2
        assert isinstance(self.filters[1], DBTimestampFilter)
        return self.filters[1]

    @property
    def addresses(self) -> Optional[List[ChecksumEthAddress]]:
        return self.address_filter.addresses

    @addresses.setter
    def addresses(self, addresses: Optional[List[ChecksumEthAddress]]) -> None:
        self.address_filter.addresses = addresses

    @property
    def from_ts(self) -> Optional[Timestamp]:
        return self.timestamp_filter.from_ts

    @from_ts.setter
    def from_ts(self, from_ts: Optional[Timestamp]) -> None:
        self.timestamp_filter.from_ts = from_ts

    @property
    def to_ts(self) -> Optional[Timestamp]:
        return self.timestamp_filter.to_ts

    @to_ts.setter
    def to_ts(self, to_ts: Optional[Timestamp]) -> None:
        self.timestamp_filter.to_ts = to_ts

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
    ) -> 'ETHTransactionsFilterQuery':
        filter_query = cls.create(
            and_op=and_op,
            limit=limit,
            offset=offset,
            order_by_attribute=order_by_attribute,
            order_ascending=order_ascending,
        )
        filters: List[DBFilter] = []
        filters.append(DBETHTransactionAddressFilter(and_op=False, addresses=addresses))
        filters.append(
            DBTimestampFilter(
                and_op=True,
                from_ts=from_ts,
                to_ts=to_ts,
            ),
        )
        filter_query.filters = filters
        return cast('ETHTransactionsFilterQuery', filter_query)
