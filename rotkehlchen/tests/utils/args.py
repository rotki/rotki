from typing import NamedTuple, Optional

from rotkehlchen.constants.misc import (
    DEFAULT_MAX_LOG_BACKUP_FILES,
    DEFAULT_MAX_LOG_SIZE_IN_MB,
    DEFAULT_SLEEP_SECS,
    DEFAULT_SQL_VM_INSTRUCTIONS_CB,
)


class ConfigurationArgs(NamedTuple):
    data_dir: Optional[str]
    ethrpc_endpoint: Optional[str]
    logfile: Optional[str]
    logtarget: Optional[str]
    loglevel: str
    logfromothermodules: bool
    sleep_secs: int = DEFAULT_SLEEP_SECS
    max_size_in_mb_all_logs: int = DEFAULT_MAX_LOG_SIZE_IN_MB
    max_logfiles_num: int = DEFAULT_MAX_LOG_BACKUP_FILES
    sqlite_instructions: int = DEFAULT_SQL_VM_INSTRUCTIONS_CB


def default_args(
        data_dir: Optional[str] = None,
        ethrpc_endpoint: Optional[str] = None,
        sleep_secs: int = DEFAULT_SLEEP_SECS,
):
    return ConfigurationArgs(
        loglevel='debug',
        logfromothermodules=False,
        sleep_secs=sleep_secs,
        data_dir=data_dir,
        ethrpc_endpoint=ethrpc_endpoint,
        max_size_in_mb_all_logs=DEFAULT_MAX_LOG_SIZE_IN_MB,
        max_logfiles_num=DEFAULT_MAX_LOG_BACKUP_FILES,
        sqlite_instructions=DEFAULT_SQL_VM_INSTRUCTIONS_CB,
        logfile=None,
        logtarget=None,
    )
