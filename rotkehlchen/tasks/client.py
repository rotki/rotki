from typing import Literal

import gevent
import zmq

from rotkehlchen.protobufs import all_common_pb2, bg_worker_pb2
from rotkehlchen.protobufs.serialization import (
    ENUM_TO_PROCESS_ERROR,
    PROCESS_CONNECTION_ADDRESS,
    ErrorType,
    to_typed_data,
)
from rotkehlchen.types import ChecksumEvmAddress


class ContextError(Exception):
    """Intended to be raised when something is wrong with db context management"""


class UnknownBGWorkerError(Exception):
    """Raised when we get an unknown error from the Task Manager background process"""


class SharedSet(set):
    """A wrapper of set to shared the same state between processes."""

    def __init__(self, zmq_connection: zmq.Socket) -> None:
        self.zmq_connection = zmq_connection

    def add(self, value: str) -> None:
        super().add(value)
        call_data = all_common_pb2.Set()  # type: ignore[attr-defined]  # pylint: disable=no-member
        call_data.method = 'add'
        call_data.data = to_typed_data(value)
        self.zmq_connection.send(call_data.SerializeToString())
        self.zmq_connection.recv()


class TaskManagerClient:
    def __init__(self, bg_worker_port: int) -> None:
        self.zmq_connection = zmq.Context().socket(zmq.REQ)
        self.zmq_connection.connect(f'{PROCESS_CONNECTION_ADDRESS}:{bg_worker_port}')
        self.base_entries_ignore_set = SharedSet(zmq_connection=self.zmq_connection)

    def _send(self, call_data: bg_worker_pb2.BGCallData) -> None:  # type: ignore[name-defined]  # pylint: disable=no-member
        self.zmq_connection.send(call_data.SerializeToString())
        response_serialized = self.zmq_connection.recv()
        return_data = bg_worker_pb2.BGReturnData()  # type: ignore[attr-defined]  # pylint: disable=no-member
        return_data.ParseFromString(response_serialized)
        if return_data.HasField('error'):
            if return_data.error.name == ErrorType.UnknownError:
                raise UnknownBGWorkerError(f'Got unknown DB error with message {return_data.error.message}')  # noqa: E501
            # raise the same error that is raised by the DBWriter process
            raise ENUM_TO_PROCESS_ERROR[return_data.error.name](return_data.error.message)

    def unlock(
            self,
            user: str,
            password: str,
            sync_approval: Literal['yes', 'no', 'unknown'],
            resume_from_backup: bool,
            sync_database: bool = True,
    ) -> None:
        call_data = bg_worker_pb2.BGCallData()  # type: ignore[attr-defined]  # pylint: disable=no-member
        unlock_call = all_common_pb2.UnlockCall(  # type: ignore[attr-defined]  # pylint: disable=no-member
            username=user,
            password=password,
            sync_approval=getattr(all_common_pb2.SyncApproval, sync_approval.upper()),  # type: ignore[attr-defined]  # pylint: disable=no-member
            resume_from_backup=resume_from_backup,
            sync_database=sync_database,
        )
        call_data.unlock.CopyFrom(unlock_call)
        gevent.wait([gevent.spawn(self._send, call_data)])

    def should_schedule(self, should_schedule: bool) -> None:
        call_data = bg_worker_pb2.BGCallData()  # type: ignore[attr-defined]  # pylint: disable=no-member
        call_data.should_schedule = should_schedule
        self._send(call_data)

    def main_loop(self) -> None:
        call_data = bg_worker_pb2.BGCallData()  # type: ignore[attr-defined]  # pylint: disable=no-member
        call_data.method = bg_worker_pb2.SchedulerMethod.SCHEDULE  # type: ignore[attr-defined]  # pylint: disable=no-member
        self._send(call_data)

    def maybe_kill_running_tx_query_tasks(self, addresses: list[ChecksumEvmAddress]) -> None:
        call_data = bg_worker_pb2.BGCallData()  # type: ignore[attr-defined]  # pylint: disable=no-member
        call_data.maybe_kill_tx_query.array.extend(addresses)
        self._send(call_data)

    def refresh_premium_credentials(self) -> None:
        call_data = bg_worker_pb2.BGCallData()  # type: ignore[attr-defined]  # pylint: disable=no-member
        call_data.method = bg_worker_pb2.SchedulerMethod.REFRESH_PREMIUM  # type: ignore[attr-defined]  # pylint: disable=no-member
        self._send(call_data)

    def logout(self) -> None:
        call_data = bg_worker_pb2.BGCallData()  # type: ignore[attr-defined]  # pylint: disable=no-member
        call_data.method = bg_worker_pb2.SchedulerMethod.CLEAR  # type: ignore[attr-defined]  # pylint: disable=no-member
        self._send(call_data)
