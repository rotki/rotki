from dataclasses import dataclass
from typing import Any, List, NamedTuple, Optional, Tuple

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
    address: Optional[ChecksumEthAddress] = None

    def prepare(self) -> Tuple[List[str], List[Any]]:
        filters = []
        bindings = []
        if self.address is not None:
            filters = ['from_address = ?', 'to_address = ?']
            bindings = [self.address, self.address]

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
