from collections import namedtuple
from typing import Optional

from rotkehlchen.constants.misc import (
    DEFAULT_MAX_LOG_BACKUP_FILES,
    DEFAULT_MAX_LOG_SIZE_IN_MB,
    DEFAULT_SQL_VM_INSTRUCTIONS_CB,
)

ConfigurationArgs = namedtuple('ConfigurationArgs', [
    'sleep_secs',
    'data_dir',
    'ethrpc_endpoint',
    'logfile',
    'logtarget',
    'loglevel',
    'logfromothermodules',
    'max_size_in_mb_all_logs',
    'max_logfiles_num',
    'sqlite_instructions',
])


def default_args(data_dir: Optional[str] = None, ethrpc_endpoint: Optional[str] = None):
    args = ConfigurationArgs(
        loglevel='debug',
        logfromothermodules=False,
        sleep_secs=60,
        data_dir=data_dir,
        ethrpc_endpoint=ethrpc_endpoint,
        max_size_in_mb_all_logs=DEFAULT_MAX_LOG_SIZE_IN_MB,
        max_logfiles_num=DEFAULT_MAX_LOG_BACKUP_FILES,
        sqlite_instructions=DEFAULT_SQL_VM_INSTRUCTIONS_CB,
        logfile=None,
        logtarget=None,
    )
    return args


def custom_config_args(data_dir: Optional[str] = None, ethrpc_endpoint: Optional[str] = None):
    """Modify the max_logfiles_num configuration to test the configuration endpoint"""
    args = ConfigurationArgs(
        loglevel='debug',
        logfromothermodules=False,
        sleep_secs=60,
        data_dir=data_dir,
        ethrpc_endpoint=ethrpc_endpoint,
        max_size_in_mb_all_logs=DEFAULT_MAX_LOG_SIZE_IN_MB,
        max_logfiles_num=30,
        sqlite_instructions=DEFAULT_SQL_VM_INSTRUCTIONS_CB,
        logfile=None,
        logtarget=None,
    )
    return args
