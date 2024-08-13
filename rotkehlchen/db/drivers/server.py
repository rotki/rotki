import os
import signal
import sqlite3
import sys
from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum, auto
from types import FrameType
from typing import Any, Final, TypeAlias, TypedDict

import zmq
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.args import app_args
from rotkehlchen.utils.mixins.enums import SerializableEnumNameMixin

UnderlyingCursor: TypeAlias = sqlite3.Cursor | sqlcipher.Cursor  # pylint: disable=no-member
UnderlyingConnection: TypeAlias = sqlite3.Connection | sqlcipher.Connection  # pylint: disable=no-member


class DBConnectionType(Enum):
    USER = auto()
    TRANSIENT = auto()
    GLOBAL = auto()


DB_CONNECTION_ADDRESS: Final = 'tcp://localhost'
DEFAULT_DB_WRITER_PORT: Final = 5555


class SerializedZMQCallData(TypedDict):
    """Dictionary type for serialized ZMQ call data"""
    connection_type: int
    db_path: str
    cursor_name: str | None
    method: str
    args: Sequence[Any]
    kwargs: dict[str, Any]


class SerializedDBWriteResult(TypedDict):
    """Dictionary type for serialized DB write result"""
    rowcount: int
    lastrowid: int


class SerializedZMQReturnData(TypedDict):
    """Dictionary type for serialized ZMQ return data"""
    result: SerializedDBWriteResult | None
    error: Any


class DbMethod(SerializableEnumNameMixin):
    INITIALIZE = auto()
    OPEN_CURSOR = auto()
    CLOSE_CURSOR = auto()
    EXECUTE = auto()
    EXECUTEMANY = auto()
    EXECUTESCRIPT = auto()
    ROLLBACK = auto()
    COMMIT = auto()
    CLOSE = auto()


@dataclass
class ZMQCallData:
    """The data packet sent through ZMQ call"""
    connection_type: DBConnectionType
    db_path: str
    cursor_name: str | None
    method: DbMethod
    args: Sequence[Any]
    kwargs: dict[str, Any]


class DBWriteResult(TypedDict):
    rowcount: int
    lastrowid: int


@dataclass()
class ZMQReturnData:
    """The data packet received from ZMQ call"""
    result: DBWriteResult | None
    error: BaseException | None

    def serialize(self) -> SerializedZMQReturnData:
        return {
            'result': self.result,
            'error': self.error,
        }

    @classmethod
    def deserialize(cls, data: SerializedZMQReturnData) -> 'ZMQReturnData':
        return cls(
            result=data['result'],
            error=data['error'],
        )


class DBWriterServer:
    """Server that listens for ZMQ messages and executes DB operations.

    Listens on a ZMQ REP socket and executes DB operations based on the messages
    it receives. The messages are of type ZMQCallData and contain information
    about the DB operation to be executed. The server will respond with a
    ZMQReturnData message containing the result of the operation or an error if it fails.
    """

    def __init__(self, port: int) -> None:
        self.db_connections: dict[str, UnderlyingConnection] = {}
        self.zmq_connection = zmq.Context().socket(zmq.REP)
        self.zmq_connection.bind(f'{DB_CONNECTION_ADDRESS}:{port}')
        self.db_cursors: defaultdict[str, defaultdict[str, UnderlyingCursor | None]] = defaultdict(defaultdict)  # noqa: E501
        # a flag to gracefully shut down the server and
        # to avoid sending back error from the server while terminating.
        self.shutting_down = False

    def _handle_connection(self, call_data: ZMQCallData) -> None:
        connect_func = sqlite3.connect if call_data.connection_type.value == DBConnectionType.GLOBAL.value else sqlcipher.connect  # noqa: E501  # pylint: disable=no-member
        self.db_connections[call_data.db_path] = connect_func(*call_data.args, **call_data.kwargs)

    def _handle_query(
            self,
            db_connection: UnderlyingConnection,
            call_data: ZMQCallData,
    ) -> ZMQReturnData:
        """Handle a query by getting the starting reference (cursor or connection)
        and calling the method on it.

        May Raise:
            KeyError: If the cursor name is specified but no cursor is found.
            AttributeError: If the method is not found on the starting reference."""
        # Get the starting reference (cursor or connection).
        starting_reference: UnderlyingConnection | UnderlyingCursor
        if call_data.cursor_name is not None:
            # If a cursor name is specified, get the cursor from db_cursors.
            starting_reference = self.db_cursors[call_data.db_path][call_data.cursor_name]
            if starting_reference is None:
                # If no cursor is found, raise a KeyError.
                raise KeyError(f'No cursor for {call_data.db_path} found')
        else:
            # If no cursor name is specified, use the database connection.
            starting_reference = db_connection

        # Call the method on the starting reference with the specified arguments
        return getattr(starting_reference, call_data.method.serialize())(*call_data.args, **call_data.kwargs)  # noqa: E501

    def listen(self) -> None:
        while True:
            try:
                call_data: ZMQCallData = self.zmq_connection.recv_pyobj()
                if call_data.method.value == DbMethod.INITIALIZE.value:
                    self._handle_connection(call_data)
                    self.zmq_connection.send_pyobj(None)
                    continue

                try:
                    db_connection = self.db_connections[call_data.db_path]
                except KeyError:
                    self.zmq_connection.send_pyobj(ZMQReturnData(
                        result=None,
                        error=KeyError(f'No DB connection for {call_data.connection_type} found'),
                    ).serialize())
                    continue

                if call_data.method.value == DbMethod.OPEN_CURSOR.value:
                    if self.db_cursors[call_data.db_path].get(call_data.cursor_name or 'default') is not None:  # noqa: E501
                        raise KeyError(f'Cursor for {call_data.db_path} already exists')
                    self.db_cursors[call_data.db_path][call_data.cursor_name or 'default'] = db_connection.cursor()  # noqa: E501
                    self.zmq_connection.send_pyobj(None)
                    continue
                if call_data.method.value == DbMethod.CLOSE_CURSOR.value:
                    del self.db_cursors[call_data.db_path][call_data.cursor_name or 'default']
                    self.zmq_connection.send_pyobj(None)
                    continue

                result = self._handle_query(db_connection, call_data)

            except BaseException as e:
                if self.shutting_down:
                    break  # The server is shutting down, don't try to send an error reply
                self.zmq_connection.send_pyobj(ZMQReturnData(result=None, error=e).serialize())

            else:
                return_data = ZMQReturnData(
                    result=DBWriteResult(
                        lastrowid=getattr(result, 'lastrowid', 0),
                        rowcount=getattr(result, 'rowcount', 0),
                    ),
                    error=None,
                )
                if return_data.result is None and return_data.error is None:
                    self.zmq_connection.send_pyobj(None)
                else:
                    self.zmq_connection.send_pyobj(return_data.serialize())

    def shutdown(self, signum: int, frame: FrameType | None = None) -> None:  # pylint: disable=unused-argument
        if self.shutting_down:
            return
        self.shutting_down = True
        sys.exit(signum)


def main() -> None:
    parser = app_args(
        prog='rotki db writer',
        description='The rotki db writer process to execute write operations on the database.',
    )

    server = DBWriterServer(parser.parse_args().db_api_port)
    signal.signal(signal.SIGINT, server.shutdown)
    if os.name != 'nt':
        signal.signal(signal.SIGTERM, server.shutdown)
        signal.signal(signal.SIGQUIT, server.shutdown)
    else:
        # Handle the windows control signal as stated here: https://pyinstaller.org/en/stable/feature-notes.html#signal-handling-in-console-windows-applications-and-onefile-application-cleanup  # noqa: E501
        # This logic handles the signal sent from the bootloader equivalent to sigterm in
        # addition to the signals sent by windows's taskkill.
        # Research documented in https://github.com/yabirgb/rotki-python-research
        import win32api  # pylint: disable=import-outside-toplevel  # isort:skip
        win32api.SetConsoleCtrlHandler(server.shutdown, True)

    server.listen()


if __name__ == '__main__':
    main()
