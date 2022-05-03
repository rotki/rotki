#!/usr/bin/python3
import json
import logging
import os
import shutil
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger('monitor')
logging.basicConfig(level=logging.DEBUG)

DEFAULT_LOG_LEVEL = 'critical'


def can_delete(file: Path, cutoff: int) -> bool:
    return int(os.stat(file).st_mtime) <= cutoff or file.name.startswith('_MEI')


def cleanup_tmp() -> None:
    logger.info('Preparing to cleanup tmp directory')
    tmp_dir = Path('/tmp/').glob('*')
    cache_cutoff = datetime.today() - timedelta(hours=6)
    cutoff_epoch = int(cache_cutoff.strftime("%s"))
    to_delete = filter(lambda x: can_delete(x, cutoff_epoch), tmp_dir)

    deleted = 0
    skipped = 0

    for item in to_delete:
        path = Path(item)
        if path.is_file():
            try:
                path.unlink()
                deleted += 1
                continue
            except PermissionError:
                skipped += 1
                continue

        try:
            shutil.rmtree(item)
            deleted += 1
        except OSError:
            skipped += 1
            continue

    logger.info(f'Deleted {deleted} files or directories, skipped {skipped} from /tmp')


def load_config_from_file() -> Optional[Dict[str, Any]]:
    config_file = Path('/config/rotki_config.json')
    if not config_file.exists():
        logger.info('no config file provided')
        return None

    with open(config_file) as file:
        try:
            data = json.load(file)
            return data
        except json.JSONDecodeError as e:
            logger.error(e)
            return None


def load_config_from_env() -> Dict[str, Any]:
    loglevel = os.environ.get('LOGLEVEL')
    logfromothermodules = os.environ.get('LOGFROMOTHERMODDULES')
    sleep_secs = os.environ.get('SLEEP_SECS')
    max_size_in_mb_all_logs = os.environ.get('MAX_SIZE_IN_MB_ALL_LOGS')
    max_logfiles_num = os.environ.get('MAX_LOGFILES_NUM')

    return {
        'loglevel': loglevel,
        'logfromothermodules': logfromothermodules,
        'sleep_secs': sleep_secs,
        'max_logfiles_num': max_logfiles_num,
        'max_size_in_mb_all_logs': max_size_in_mb_all_logs,
    }


def load_config() -> List[str]:
    env_config = load_config_from_env()
    file_config = load_config_from_file()

    logger.info('loading config from env')

    loglevel = env_config.get('loglevel')
    log_from_other_modules = env_config.get('logfromothermodules')
    sleep_secs = env_config.get('sleep_secs')
    max_logfiles_num = env_config.get('max_logfiles_num')
    max_size_in_mb_all_logs = env_config.get('max_size_in_mb_all_logs')

    if file_config is not None:
        logger.info('loading config from file')

        if file_config.get('loglevel') is not None:
            loglevel = file_config.get('loglevel')

        if file_config.get('logfromothermodules') is not None:
            log_from_other_modules = file_config.get('logfromothermodules')

        if file_config.get('sleep-secs') is not None:
            sleep_secs = file_config.get('sleep-secs')

        if file_config.get('max_logfiles_num') is not None:
            max_logfiles_num = file_config.get('max_logfiles_num')

        if file_config.get('max_size_in_mb_all_logs') is not None:
            max_size_in_mb_all_logs = file_config.get('max_size_in_mb_all_logs')

    args = [
        '--data-dir',
        '/data',
        '--logfile',
        '/logs/rotki.log',
        '--loglevel',
        loglevel if loglevel is not None else DEFAULT_LOG_LEVEL,
    ]

    if log_from_other_modules is True:
        args.append('--logfromothermodules')

    if sleep_secs is not None:
        args.append('--sleep-secs')
        args.append(str(sleep_secs))

    if max_logfiles_num is not None:
        args.append('--max-logfiles-num')
        args.append(str(max_logfiles_num))

    if max_size_in_mb_all_logs is not None:
        args.append('--max-size-in-mb-all-logs')
        args.append(str(max_size_in_mb_all_logs))

    return args


cleanup_tmp()

base_args = [
    '/usr/sbin/rotki',
    '--rest-api-port',
    '4242',
    '--websockets-api-port',
    '4243',
    '--api-cors',
    'http://localhost:*/*,app://.',
    '--api-host',
    '0.0.0.0',
]

config_args = load_config()
cmd = base_args + config_args

logger.info('starting rotki backend')

rotki = subprocess.Popen(cmd)

if rotki.returncode == 1:
    logger.error('Failed to start rotki')
    exit(1)

logger.info('starting nginx')

nginx = subprocess.Popen('nginx -g "daemon off;"', shell=True)

if nginx.returncode == 1:
    logger.error('Failed to start nginx')
    exit(1)

while True:
    time.sleep(60)

    if rotki.poll() is not None:
        logger.error('rotki has terminated exiting')
        exit(1)

    if nginx.poll() is not None:
        logger.error('nginx was not running')
        exit(1)

    logger.info('OK: processes still running')
