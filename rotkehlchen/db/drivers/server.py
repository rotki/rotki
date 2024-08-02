import os
import sqlite3
import sys
from collections import defaultdict
from collections.abc import Sequence
from enum import Enum, auto
from pathlib import Path
from signal import SIGINT, SIGQUIT, SIGTERM, signal
from typing import Any, TypeAlias, TypedDict

import zmq
from pysqlcipher3 import dbapi2 as sqlcipher

UnderlyingCursor: TypeAlias = sqlite3.Cursor | sqlcipher.Cursor  # pylint: disable=no-member
UnderlyingConnection: TypeAlias = sqlite3.Connection | sqlcipher.Connection  # pylint: disable=no-member


class DBConnectionType(Enum):
    USER = auto()
    TRANSIENT = auto()
    GLOBAL = auto()


DB_CONNECTION_ADDRESS = 'tcp://localhost:5555'


class SerializedZMQCallData(TypedDict):
    connection_type: int
    use_cursor: bool
    method: str
    args: Sequence[Any]
    kwargs: dict[str, Any]


class SerializedDBWriteResult(TypedDict):
    rowcount: int
    lastrowid: int


class SerializedZMQReturnData(TypedDict):
    result: SerializedDBWriteResult | None
    error: Any


class DBDetails:
    path: Path
    connection_type: DBConnectionType
    sqlite_vm_instructions: int

    def __init__(
            self,
            path: Path,
            connection_type: DBConnectionType,
            sqlite_vm_instructions: int,
    ) -> None:
        self.path = path
        self.connection_type = connection_type
        self.sqlite_vm_instructions = sqlite_vm_instructions


class ZMQCallData:
    """The data packet sent through ZMQ call"""
    connection_type: DBConnectionType
    use_cursor: bool
    method: str
    args: Sequence[Any]
    kwargs: dict[str, Any]

    def __init__(
            self,
            connection_type: DBConnectionType,
            use_cursor: bool,
            method: str,
            args: Sequence[Any],
            kwargs: dict[str, Any],
    ) -> None:
        self.connection_type = connection_type
        self.use_cursor = use_cursor
        self.method = method
        self.args = args
        self.kwargs = kwargs

    def __str__(self) -> str:
        return f'ZMQCallData(connection_type={self.connection_type}, method={self.method}, args={self.args}, kwargs={self.kwargs})'  # noqa: E501

    def serialize(self) -> SerializedZMQCallData:
        return {
            'connection_type': self.connection_type.value,
            'use_cursor': self.use_cursor,
            'method': self.method,
            'args': self.args,
            'kwargs': self.kwargs,
        }

    @classmethod
    def deserialize(cls, data: SerializedZMQCallData) -> 'ZMQCallData':
        return cls(
            connection_type=DBConnectionType(data['connection_type']),
            use_cursor=data['use_cursor'],
            method=data['method'],
            args=data['args'],
            kwargs=data['kwargs'],
        )


class DBWriteResult(TypedDict):
    rowcount: int
    lastrowid: int


class ZMQReturnData:
    """The data packet received from ZMQ call"""
    result: DBWriteResult | None
    error: BaseException | None

    def __init__(
            self,
            result: DBWriteResult | None = None,
            error: BaseException | None = None,
    ) -> None:
        self.result = result
        self.error = error

    def __str__(self) -> str:
        return f'ZMQReturnData(result={self.result}, error={self.error})'

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

    def __init__(self) -> None:
        self.db_connections: dict[int, UnderlyingConnection] = {}
        self.zmq_connection = zmq.Context().socket(zmq.REP)
        self.zmq_connection.bind(DB_CONNECTION_ADDRESS)
        self.db_cursors: defaultdict[int, UnderlyingCursor | None] = defaultdict(None)
        self.shutting_down = False

    def _handle_connection(self, call_data: ZMQCallData) -> None:
        connect_func = sqlite3.connect if call_data.connection_type == DBConnectionType.GLOBAL else sqlcipher.connect  # noqa: E501  # pylint: disable=no-member
        self.db_connections[call_data.connection_type.value] = connect_func(*call_data.args, **call_data.kwargs)  # noqa: E501

    def _handle_query(
            self,
            db_connection: UnderlyingConnection,
            call_data: ZMQCallData,
    ) -> ZMQReturnData:
        starting_reference: UnderlyingConnection | UnderlyingCursor
        if call_data.use_cursor:
            starting_reference = self.db_cursors[call_data.connection_type.value]
            if starting_reference is None:
                raise KeyError(f'No cursor for {call_data.connection_type} found')
        else:
            starting_reference = db_connection

        return getattr(starting_reference, call_data.method)(*call_data.args, **call_data.kwargs)

    def listen(self) -> None:
        while True:
            try:
                call_data: ZMQCallData = self.zmq_connection.recv_pyobj()
                if call_data.method == '__init__':
                    self._handle_connection(call_data)
                    self.zmq_connection.send_pyobj(None)
                    continue

                try:
                    db_connection = self.db_connections[call_data.connection_type.value]
                except KeyError:
                    self.zmq_connection.send_pyobj(ZMQReturnData(
                        error=KeyError(f'No DB connection for {call_data.connection_type} found'),
                    ))
                    continue

                if call_data.method == '*open_cursor*':
                    self.db_cursors[call_data.connection_type.value] = db_connection.cursor()
                    self.zmq_connection.send_pyobj(None)
                    continue
                if call_data.method == '*close_cursor*':
                    del self.db_cursors[call_data.connection_type.value]
                    self.zmq_connection.send_pyobj(None)
                    continue

                result = self._handle_query(db_connection, call_data)

            except BaseException as e:
                if self.shutting_down:
                    break
                self.zmq_connection.send_pyobj(ZMQReturnData(error=e))

            else:
                return_data = ZMQReturnData(result=DBWriteResult(
                    lastrowid=getattr(result, 'lastrowid', 0),
                    rowcount=getattr(result, 'rowcount', 0),
                ))
                if return_data.result is None and return_data.error is None:
                    self.zmq_connection.send_pyobj(None)
                else:
                    self.zmq_connection.send_pyobj(return_data)

    def shutdown(self, signum: int, frame: Any) -> None:  # pylint: disable=unused-argument
        if self.shutting_down:
            return
        self.shutting_down = True
        sys.exit(0)


def main() -> None:
    server = DBWriterServer()
    signal(SIGINT, server.shutdown)
    if os.name != 'nt':
        signal(SIGTERM, server.shutdown)
        signal(SIGQUIT, server.shutdown)
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
