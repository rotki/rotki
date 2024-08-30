import os
import signal
import sqlite3
import sys
from collections import defaultdict
from enum import Enum, auto
from types import FrameType
from typing import Final, TypeAlias

import zmq
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.args import app_args
from rotkehlchen.db.drivers import db_messages_pb2
from rotkehlchen.fval import INT_MAX_PRECISION

UnderlyingCursor: TypeAlias = sqlite3.Cursor | sqlcipher.Cursor  # pylint: disable=no-member
UnderlyingConnection: TypeAlias = sqlite3.Connection | sqlcipher.Connection  # pylint: disable=no-member
SerializableTypes: TypeAlias = list | tuple | bytes | str | bool | int | float | None
DBMethod = db_messages_pb2.DBMethod  # type: ignore[attr-defined]  # pylint: disable=no-member
DBError = db_messages_pb2.DBError  # type: ignore[attr-defined]  # pylint: disable=no-member


class DBWriteError(
    sqlite3.DataError,
    sqlite3.IntegrityError,
    sqlite3.InterfaceError,
    sqlite3.InternalError,
    sqlite3.NotSupportedError,
    sqlite3.OperationalError,
    sqlite3.ProgrammingError,
    sqlcipher.DataError,  # pylint: disable=no-member
    sqlcipher.IntegrityError,  # pylint: disable=no-member
    sqlcipher.InterfaceError,  # pylint: disable=no-member
    sqlcipher.InternalError,  # pylint: disable=no-member
    sqlcipher.NotSupportedError,  # pylint: disable=no-member
    sqlcipher.OperationalError,  # pylint: disable=no-member
    sqlcipher.ProgrammingError,  # pylint: disable=no-member
):
    """Raised when we get an error while writing to the DB"""


class ComputationError(FloatingPointError, OverflowError, ZeroDivisionError, UnicodeError):
    """Raised while calculating a value"""


class ProgrammingError(
    AssertionError,
    AttributeError,
    EOFError,
    GeneratorExit,
    NotImplementedError,
    RecursionError,
    ReferenceError,
    TypeError,
    ValueError,
):
    """Raised due to a mistake in the code by the programmer"""


class HostSystemError(
    KeyboardInterrupt,
    BlockingIOError,
    ConnectionError,
    PermissionError,
    TimeoutError,
    SystemError,
):
    """Raised for errors related to the host system"""


class MemoryUsageError(IndexError, KeyError, MemoryError, StopIteration):
    """Raised when using the memory in a wrong way"""


DB_CONNECTION_ADDRESS: Final = 'tcp://localhost'
DEFAULT_DB_WRITER_PORT: Final = 5555
DB_ERROR_TO_ENUM = {
    MemoryUsageError: DBError.MemoryError,
    HostSystemError: DBError.HostSystemError,
    ProgrammingError: DBError.ProgrammingError,
    ComputationError: DBError.ComputationError,
    DBWriteError: DBError.DBWriteError,
}
ENUM_TO_DB_ERROR = {value: key for key, value in DB_ERROR_TO_ENUM.items()}


class DBConnectionType(Enum):
    USER = 0  # start with 0 to keep consistent with protobuf enum
    TRANSIENT = auto()
    GLOBAL = auto()


def to_typed_data(data: SerializableTypes) -> db_messages_pb2.TypedData:  # type: ignore[name-defined]  # pylint: disable=no-member
    """Converts a python object to a protobuf TypedData object"""
    typed_data = db_messages_pb2.TypedData()  # type: ignore[attr-defined]  # pylint: disable=no-member
    if isinstance(data, list | tuple):
        typed_data.type = 'array'
        typed_array = db_messages_pb2.TypedArray()  # type: ignore[attr-defined]  # pylint: disable=no-member
        typed_array.array.extend([to_typed_data(item) for item in data])
        typed_data.array.CopyFrom(typed_array)
    elif isinstance(data, bytes):
        typed_data.type = 'bytes'
        typed_data.bytes = data
    elif isinstance(data, str):
        typed_data.type = 'string'
        typed_data.bytes = data.encode()
    elif isinstance(data, bool):
        typed_data.type = 'bool'
        typed_data.bytes = data.to_bytes()
    elif isinstance(data, int):
        typed_data.type = 'int'
        typed_data.bytes = data.to_bytes(length=INT_MAX_PRECISION, byteorder='big', signed=True)
    elif isinstance(data, float):
        typed_data.type = 'float'
        typed_data.bytes = data.hex().encode()
    elif data is None:
        typed_data.type = 'null'
        typed_data.bytes = b''
    else:
        raise NotImplementedError(f'Trying to send unsupported data {data}')
    return typed_data


def from_typed_data(data: db_messages_pb2.TypedData) -> SerializableTypes:  # type: ignore[name-defined]  # pylint: disable=no-member
    """Converts a protobuf TypedData object to a python object"""
    if data.type == 'array':
        return [from_typed_data(item) for item in data.array.array]
    if data.type == 'bytes':
        return data.bytes
    if data.type == 'string':
        return data.bytes.decode()
    if data.type == 'int':
        return int.from_bytes(data.bytes, byteorder='big', signed=True)
    if data.type == 'bool':
        return bool.from_bytes(data.bytes)
    if data.type == 'float':
        return float.fromhex(data.bytes.decode())
    if data.type == 'null':
        return None
    raise NotImplementedError(f'Receiving unsupported data {data}')


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

    def _handle_connection(
            self,
            call_data: db_messages_pb2.ZMQCallData,  # type: ignore[name-defined]  # pylint: disable=no-member
            args: tuple[SerializableTypes, ...],
            kwargs: dict[str, SerializableTypes],
    ) -> None:
        connect_func = sqlite3.connect if call_data.connection_type == db_messages_pb2.DBConnectionType.GLOBAL else sqlcipher.connect  # type: ignore[attr-defined]  # pylint: disable=no-member  # noqa: E501
        self.db_connections[call_data.db_path] = connect_func(*args, **kwargs)

    def _handle_query(
            self,
            db_connection: UnderlyingConnection,
            call_data: db_messages_pb2.ZMQCallData,  # type: ignore[name-defined]  # pylint: disable=no-member
            args: tuple[SerializableTypes, ...],
            kwargs: dict[str, SerializableTypes],
    ) -> db_messages_pb2.ZMQReturnData:  # type: ignore[name-defined]  # pylint: disable=no-member
        """Handle a query by getting the starting reference (cursor or connection)
        and calling the method on it.

        May Raise:
            KeyError: If the cursor name is specified but no cursor is found.
            AttributeError: If the method is not found on the starting reference."""
        # Get the starting reference (cursor or connection).
        starting_reference: UnderlyingConnection | UnderlyingCursor
        if call_data.cursor_name != '':
            # If a cursor name is specified, get the cursor from db_cursors.
            starting_reference = self.db_cursors[call_data.db_path][call_data.cursor_name]
            if starting_reference is None:
                # If no cursor is found, raise a KeyError.
                raise KeyError(f'No cursor for {call_data.db_path} found')
        else:
            # If no cursor name is specified, use the database connection.
            starting_reference = db_connection

        return getattr(  # Call the method on the starting reference with the specified arguments
            starting_reference,
            DBMethod.Name(call_data.method).lower(),
        )(*args, **kwargs)

    def listen(self) -> None:
        while True:
            return_data = db_messages_pb2.ZMQReturnData()  # type: ignore[attr-defined]  # pylint: disable=no-member
            try:
                call_data_serialized = self.zmq_connection.recv()
                call_data = db_messages_pb2.ZMQCallData()  # type: ignore[attr-defined]  # pylint: disable=no-member
                call_data.ParseFromString(call_data_serialized)
                args = tuple(from_typed_data(data) for data in call_data.args)
                kwargs = {key: from_typed_data(data) for key, data in call_data.kwargs.items()}
                if call_data.method == DBMethod.INITIALIZE:
                    self._handle_connection(call_data, args, kwargs)
                    self.zmq_connection.send(b'')
                    continue

                try:
                    db_connection = self.db_connections[call_data.db_path]
                except KeyError as e:
                    raise KeyError(f'No DB connection for {DBConnectionType(call_data.connection_type)} found') from e  # noqa: E501

                cursor_name = call_data.cursor_name or 'default'
                if call_data.method == DBMethod.OPEN_CURSOR:
                    if self.db_cursors[call_data.db_path].get(cursor_name) is not None:
                        raise KeyError(f'Cursor "{cursor_name}" for {call_data.db_path} already exists')  # noqa: E501
                    self.db_cursors[call_data.db_path][cursor_name] = db_connection.cursor()
                    self.zmq_connection.send(b'')
                    continue
                if call_data.method == DBMethod.CLOSE_CURSOR:
                    self.db_cursors[call_data.db_path].pop(cursor_name, None)
                    self.zmq_connection.send(b'')
                    continue

                result = self._handle_query(db_connection, call_data, args, kwargs)
            except BaseException as e:
                if self.shutting_down:
                    break  # The server is shutting down, don't try to send an error reply
                db_writer_error = db_messages_pb2.DBWriterError()  # type: ignore[attr-defined]  # pylint: disable=no-member
                for exception_type in DB_ERROR_TO_ENUM:
                    if issubclass(exception_type, e.__class__):
                        db_writer_error.name = DB_ERROR_TO_ENUM.get(exception_type, DBError.UnknownError)  # noqa: E501
                        break
                else:
                    db_writer_error.name = DBError.UnknownError
                db_writer_error.message = str(e)
                return_data.error.CopyFrom(db_writer_error)
                self.zmq_connection.send(return_data.SerializeToString())

            else:
                db_writer_result = db_messages_pb2.DBWriteResult()  # type: ignore[attr-defined]  # pylint: disable=no-member
                if (lastrowid := getattr(result, 'lastrowid', None)) is not None:
                    db_writer_result.lastrowid = lastrowid
                if (rowcount := getattr(result, 'rowcount', None)) is not None:
                    db_writer_result.rowcount = rowcount
                return_data.result.CopyFrom(db_writer_result)
                if return_data.result is None and db_writer_result.error is None:
                    self.zmq_connection.send(b'')
                else:
                    self.zmq_connection.send(return_data.SerializeToString())

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
