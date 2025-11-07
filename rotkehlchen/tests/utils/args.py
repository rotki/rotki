from typing import NamedTuple

from rotkehlchen.constants.misc import (
    DEFAULT_MAX_LOG_BACKUP_FILES,
    DEFAULT_MAX_LOG_SIZE_IN_MB,
    DEFAULT_SQL_VM_INSTRUCTIONS_CB,
)


class ConfigurationArgs(NamedTuple):
    data_dir: str | None
    ethrpc_endpoint: str | None
    logfile: str | None
    logtarget: str | None
    loglevel: str
    logfromothermodules: bool
    max_size_in_mb_all_logs: int = DEFAULT_MAX_LOG_SIZE_IN_MB
    max_logfiles_num: int = DEFAULT_MAX_LOG_BACKUP_FILES
    sqlite_instructions: int = DEFAULT_SQL_VM_INSTRUCTIONS_CB
    disable_task_manager: bool = False


def default_args(
        data_dir: str | None = None,
        ethrpc_endpoint: str | None = None,
        max_size_in_mb_all_logs: int = DEFAULT_MAX_LOG_SIZE_IN_MB,
        loglevel: str = 'DEBUG',
):
    return ConfigurationArgs(
        loglevel=loglevel,
        logfromothermodules=False,
        data_dir=data_dir,
        ethrpc_endpoint=ethrpc_endpoint,
        max_size_in_mb_all_logs=max_size_in_mb_all_logs,
        max_logfiles_num=DEFAULT_MAX_LOG_BACKUP_FILES,
        sqlite_instructions=DEFAULT_SQL_VM_INSTRUCTIONS_CB,
        logfile=None,
        logtarget=None,
        disable_task_manager=False,
    )
