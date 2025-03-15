import logging
import sqlite3
import sys
from collections import defaultdict
from enum import Enum, auto
from types import FrameType
from typing import Final, TypeAlias

import zmq
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.args import app_args
from rotkehlchen.logging import RotkehlchenLogsAdapter, configure_logging
from rotkehlchen.protobufs import all_common_pb2, db_messages_pb2
from rotkehlchen.protobufs.serialization import (
    PROCESS_CONNECTION_ADDRESS,
    PROCESS_ERROR_TO_ENUM,
    SerializableTypes,
    from_typed_data,
)
from rotkehlchen.tests.utils.args import default_args
from rotkehlchen.utils.misc import set_signal_handlers

UnderlyingCursor: TypeAlias = sqlite3.Cursor | sqlcipher.Cursor  # pylint: disable=no-member
UnderlyingConnection: TypeAlias = sqlite3.Connection | sqlcipher.Connection  # pylint: disable=no-member
DBMethod = db_messages_pb2.DBMethod  # type: ignore[attr-defined]  # pylint: disable=no-member

DEFAULT_DB_WRITER_PORT: Final = 5555


logger = logging.getLogger(__name__)
log = RotkehlchenLogsAdapter(logger)

configure_logging(default_args())


class DBConnectionType(Enum):
    USER = 0  # start with 0 to keep consistent with protobuf enum
    TRANSIENT = auto()
    GLOBAL = auto()


class DBWriterServer:
    """Server that listens for ZMQ messages and executes DB operations.

    Listens on a ZMQ REP socket and executes DB operations based on the messages
    it receives. The messages are of type DBCallData and contain information
    about the DB operation to be executed. The server will respond with a
    DBReturnData message containing the result of the operation or an error if it fails.
    """

    def __init__(self, port: int) -> None:
        self.db_connections: dict[str, UnderlyingConnection] = {}
        self.zmq_connection = zmq.Context().socket(zmq.REP)
        self.zmq_connection.bind(f'{PROCESS_CONNECTION_ADDRESS}:{port}')
        self.db_cursors: defaultdict[str, defaultdict[str, UnderlyingCursor | None]] = defaultdict(defaultdict)  # noqa: E501
        # a flag to gracefully shut down the server and
        # to avoid sending back error from the server while terminating.
        self.shutting_down = False
        log.info('DB server started')

    def _handle_connection(
            self,
            call_data: db_messages_pb2.DBCallData,  # type: ignore[name-defined]  # pylint: disable=no-member
            args: tuple[SerializableTypes, ...],
            kwargs: dict[str, SerializableTypes],
    ) -> None:
        connect_func = sqlite3.connect if call_data.connection_type == db_messages_pb2.DBConnectionType.GLOBAL else sqlcipher.connect  # type: ignore[attr-defined]  # pylint: disable=no-member  # noqa: E501
        self.db_connections[call_data.db_path] = connect_func(*args, **kwargs)  # type: ignore

    def _handle_query(
            self,
            db_connection: UnderlyingConnection,
            call_data: db_messages_pb2.DBCallData,  # type: ignore[name-defined]  # pylint: disable=no-member
            args: tuple[SerializableTypes, ...],
            kwargs: dict[str, SerializableTypes],
    ) -> db_messages_pb2.DBReturnData:  # type: ignore[name-defined]  # pylint: disable=no-member
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
            return_data = db_messages_pb2.DBReturnData()  # type: ignore[attr-defined]  # pylint: disable=no-member
            try:
                call_data_serialized = self.zmq_connection.recv()
                call_data = db_messages_pb2.DBCallData()  # type: ignore[attr-defined]  # pylint: disable=no-member
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
                    if (conn := self.db_cursors[call_data.db_path].pop(cursor_name, None)) is not None:  # noqa: E501
                        conn.close()
                    else:
                        logger.error(f'Tried to close non existing cursor {cursor_name}')

                    self.zmq_connection.send(b'')
                    continue

                result = self._handle_query(db_connection, call_data, args, kwargs)
            except BaseException as e:
                if self.shutting_down:
                    break  # The server is shutting down, don't try to send an error reply
                db_writer_error = all_common_pb2.Error()  # type: ignore[attr-defined]  # pylint: disable=no-member
                for exception_type in PROCESS_ERROR_TO_ENUM:
                    if issubclass(exception_type, e.__class__):
                        db_writer_error.name = PROCESS_ERROR_TO_ENUM.get(exception_type, all_common_pb2.ErrorType.UnknownError)  # type: ignore[attr-defined]  # pylint: disable=no-member  # noqa: E501
                        break
                else:
                    db_writer_error.name = all_common_pb2.ErrorType.UnknownError  # type: ignore[attr-defined]  # pylint: disable=no-member
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
    set_signal_handlers(server.shutdown)
    server.listen()


if __name__ == '__main__':
    main()
