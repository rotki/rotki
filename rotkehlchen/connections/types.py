"""Connectors and connections.

A connector is the implementation that fetches data, such as the Kraken exchange API client or
the FinTS protocol. A connection is one configured account of a connector: its credentials,
its user-given name and the location its data belongs to. Connector identifiers live in their
own namespace. That an exchange connector is spelled like its exchange location is incidental.
"""
import uuid
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Literal, NewType

if TYPE_CHECKING:
    from rotkehlchen.locations.types import LocationIdentifier
    from rotkehlchen.types import ApiKey, ApiSecret

ConnectorIdentifier = NewType('ConnectorIdentifier', str)
ConnectionIdentifier = NewType('ConnectionIdentifier', str)

ConnectionRangeKind = Literal['history_events', 'history_events_futures', 'margins', 'lending_history']  # noqa: E501
CONNECTION_RANGE_KINDS: Final[tuple[ConnectionRangeKind, ...]] = ('history_events', 'history_events_futures', 'margins', 'lending_history')  # noqa: E501


def new_connection_identifier() -> ConnectionIdentifier:
    return ConnectionIdentifier(str(uuid.uuid4()))


def connection_range_name(identifier: str, kind: ConnectionRangeKind) -> str:
    """The used_query_ranges name of what a connection has queried"""
    return f'{identifier}_{kind}'


def connection_cache_prefix(identifier: str) -> str:
    """The prefix of every key_value_cache entry of a connection (cursors, sessions)"""
    return f'{identifier}_'


@dataclass(frozen=True)
class IntegrationConnection:
    identifier: ConnectionIdentifier
    name: str
    connector: ConnectorIdentifier
    location: LocationIdentifier  # where the connection's events and balances belong
    api_key: ApiKey
    api_secret: ApiSecret | None
    passphrase: str | None = None
