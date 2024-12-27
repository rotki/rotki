import sqlite3
from argparse import Namespace
from typing import Final, TypeAlias

import gevent
import zmq.green as zmq
from pysqlcipher3 import dbapi2 as sqlcipher

from rotkehlchen.args import app_args
from rotkehlchen.errors.misc import GreenletKilledError
from rotkehlchen.protobufs import all_common_pb2, bg_worker_pb2
from rotkehlchen.protobufs.serialization import (
    PROCESS_CONNECTION_ADDRESS,
    PROCESS_ERROR_TO_ENUM,
    from_typed_data,
)
from rotkehlchen.rotkehlchen import Rotkehlchen
from rotkehlchen.types import ChecksumEvmAddress
from rotkehlchen.utils.misc import set_signal_handlers

UnderlyingCursor: TypeAlias = sqlite3.Cursor | sqlcipher.Cursor  # pylint: disable=no-member
UnderlyingConnection: TypeAlias = sqlite3.Connection | sqlcipher.Connection  # pylint: disable=no-member
SchedulerMethod = bg_worker_pb2.SchedulerMethod  # type: ignore[attr-defined]  # pylint: disable=no-member

DEFAULT_BG_WORKER_PORT: Final = 5556


class TaskManagerServer:
    """Server that listens for ZMQ messages and runs background tasks.

    Listens on a ZMQ REP socket and runs background tasks based on the start/stop messages
    it receives. The messages are of type SchedulerMethod which can be either 'SCHEDULE' or 'CLEAR'
    The server will respond with an empty response, after successfully processing the message.
    """

    def __init__(self, args: Namespace) -> None:
        self.zmq_connection = zmq.Context().socket(zmq.REP)
        self.zmq_connection.bind(f'{PROCESS_CONNECTION_ADDRESS}:{args.bg_worker_port}')
        # a flag to gracefully shut down the server and
        # to avoid sending back error from the server while terminating.
        self.shutting_down = False
        self.rotkehlchen = Rotkehlchen(args)
        self.tasks_greenlet: gevent.Greenlet | None = None

    def _unlock(self, call_data: all_common_pb2.UnlockCall) -> None:  # type: ignore[name-defined]  # pylint: disable=no-member
        """Unlock the rotkehlchen instance and initialize the task manager."""
        self.rotkehlchen.unlock_user(
            user=call_data.username,
            password=call_data.password,
            create_new=False,  # it should already be created from the api backend process
            sync_approval=all_common_pb2.SyncApproval.Name(call_data.sync_approval).lower(),  # type: ignore[attr-defined]  # pylint: disable=no-member
            premium_credentials=None,
            resume_from_backup=call_data.resume_from_backup,
            sync_database=call_data.sync_database,
        )

    def _maybe_kill_running_tx_query_tasks(self, addresses: list[ChecksumEvmAddress]) -> None:
        """Checks for running greenlets related to transactions query for the given
        addresses and kills them if they exist"""
        if self.rotkehlchen.task_manager is None:
            return

        tx_query_task_greenlets = self.rotkehlchen.task_manager.running_greenlets.get(
            self.rotkehlchen.task_manager._maybe_query_evm_transactions,
            [],
        )
        for greenlet in tx_query_task_greenlets:
            if greenlet.dead is False and greenlet.kwargs['address'] in addresses:
                greenlet.kill(exception=GreenletKilledError('Killed due to request for evm address removal'))  # noqa: E501

    def listen(self) -> None:
        """Listen for ZMQ messages and process them."""
        while True:
            return_data = bg_worker_pb2.BGReturnData()  # type: ignore[attr-defined]  # pylint: disable=no-member
            try:
                call_data_serialized = self.zmq_connection.recv()
                call_data = bg_worker_pb2.BGCallData()  # type: ignore[attr-defined]  # pylint: disable=no-member
                call_data.ParseFromString(call_data_serialized)
                if call_data.WhichOneof('data') == 'method':
                    if call_data.method == SchedulerMethod.SCHEDULE:
                        self.tasks_greenlet = gevent.spawn(self.rotkehlchen.main_loop)
                    elif call_data.method == SchedulerMethod.CLEAR:
                        self.rotkehlchen.logout()
                    elif call_data.method == SchedulerMethod.REFRESH_PREMIUM:
                        with self.rotkehlchen.data.db.conn.read_ctx() as cursor:
                            if (db_credentials := self.rotkehlchen.data.db.get_rotkehlchen_premium(
                                cursor=cursor,
                            )) is not None:
                                self.rotkehlchen.set_premium_credentials(
                                    credentials=db_credentials,
                                )
                    else:
                        raise ValueError(f'Invalid scheduler method received: {SchedulerMethod.Name(call_data.method)}')  # noqa: E501

                elif call_data.WhichOneof('data') == 'should_schedule':
                    if self.rotkehlchen.task_manager is None:
                        raise ValueError('The task manager is not initialized for "should_schedule" method')  # noqa: E501
                    self.rotkehlchen.task_manager.should_schedule = call_data.should_schedule

                elif call_data.WhichOneof('data') == 'unlock':
                    self._unlock(call_data.unlock)

                elif call_data.WhichOneof('data') == 'maybe_kill_tx_query':
                    self._maybe_kill_running_tx_query_tasks(call_data.maybe_kill_tx_query.array)

                elif call_data.WhichOneof('data') == 'base_entries_ignore_set':
                    if self.rotkehlchen.task_manager is None:
                        raise ValueError('The task manager is not initialized for "base_entries_ignore_set" method')  # noqa: E501
                    getattr(
                        self.rotkehlchen.task_manager.base_entries_ignore_set,
                        call_data.method,
                    )(from_typed_data(call_data.data))

                else:
                    raise ValueError(f'Invalid data received: {call_data.WhichOneof("data")}')
                self.zmq_connection.send(return_data.SerializeToString())

            except BaseException as e:
                if self.shutting_down:
                    break  # The server is shutting down, don't try to send an error reply
                bg_worker_error = all_common_pb2.Error()  # type: ignore[attr-defined]  # pylint: disable=no-member
                for exception_type in PROCESS_ERROR_TO_ENUM:
                    if issubclass(exception_type, e.__class__):
                        bg_worker_error.name = PROCESS_ERROR_TO_ENUM.get(exception_type, all_common_pb2.ErrorType.UnknownError)  # type: ignore[attr-defined]  # pylint: disable=no-member  # noqa: E501
                        break
                else:
                    bg_worker_error.name = all_common_pb2.ErrorType.UnknownError  # type: ignore[attr-defined]  # pylint: disable=no-member
                bg_worker_error.message = str(e)
                return_data.error.CopyFrom(bg_worker_error)
                self.zmq_connection.send(return_data.SerializeToString())

    def shutdown(self) -> None:
        if self.shutting_down:
            return
        self.zmq_connection.close()
        self.active = False
        self.shutting_down = True
        if self.tasks_greenlet is not None:
            self.tasks_greenlet.kill(block=False)
        self.rotkehlchen.shutdown()


def main() -> None:
    parser = app_args(
        prog='rotki bg worker',
        description='The rotki bg worker process to run background tasks.',
    )

    server = TaskManagerServer(parser.parse_args())
    set_signal_handlers(server.shutdown)
    server.listen()


if __name__ == '__main__':
    main()
