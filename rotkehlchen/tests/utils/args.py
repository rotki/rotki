from collections import namedtuple
from typing import Optional

from rotkehlchen.args import DEFAULT_MAX_LOG_BACKUP_FILES, DEFAULT_MAX_LOG_SIZE_IN_MB


def default_args(data_dir: Optional[str] = None, ethrpc_endpoint: Optional[str] = None):
    args = namedtuple('args', [
        'sleep_secs',
        'data_dir',
        'ethrpc_endpoint',
        'logfile',
        'logtarget',
        'loglevel',
        'logfromothermodules',
        'max_size_in_mb_all_logs',
        'max_logfiles_num',
    ])
    args.loglevel = 'debug'
    args.logfromothermodules = False
    args.sleep_secs = 60
    args.data_dir = data_dir
    args.ethrpc_endpoint = ethrpc_endpoint
    args.max_size_in_mb_all_logs = DEFAULT_MAX_LOG_SIZE_IN_MB
    args.max_logfiles_num = DEFAULT_MAX_LOG_BACKUP_FILES
    return args
