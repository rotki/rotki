import sqlite3
from typing import Final, TypeAlias

from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.fval import INT_MAX_PRECISION
from rotkehlchen.protobufs import all_common_pb2

ErrorType = all_common_pb2.ErrorType  # type: ignore[attr-defined]  # pylint: disable=no-member
SerializableTypes: TypeAlias = list | tuple | bytes | str | bool | int | float | None


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


PROCESS_CONNECTION_ADDRESS: Final = 'tcp://localhost'
PROCESS_ERROR_TO_ENUM = {
    MemoryUsageError: ErrorType.MemoryError,
    HostSystemError: ErrorType.HostSystemError,
    ProgrammingError: ErrorType.ProgrammingError,
    ComputationError: ErrorType.ComputationError,
    DBWriteError: ErrorType.DBWriteError,
}
ENUM_TO_PROCESS_ERROR = {value: key for key, value in PROCESS_ERROR_TO_ENUM.items()}


def to_typed_data(data: SerializableTypes) -> all_common_pb2.TypedData:  # type: ignore[name-defined]  # pylint: disable=no-member
    """Converts a python object to a protobuf TypedData object"""
    typed_data = all_common_pb2.TypedData()  # type: ignore[attr-defined]  # pylint: disable=no-member
    if isinstance(data, list | tuple):
        typed_data.type = 'array'
        typed_array = all_common_pb2.TypedArray()  # type: ignore[attr-defined]  # pylint: disable=no-member
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


def from_typed_data(data: all_common_pb2.TypedData) -> SerializableTypes:  # type: ignore[name-defined]  # pylint: disable=no-member
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
