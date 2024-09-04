#!/usr/bin/python3
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from signal import SIGINT, SIGQUIT, SIGTERM, signal
from types import FrameType
from typing import Any

logger = logging.getLogger('monitor')
logging.basicConfig(level=logging.DEBUG)

DEFAULT_LOG_LEVEL = 'critical'


def can_delete(file: Path, cutoff: int) -> bool:
    return int(os.stat(file).st_mtime) <= cutoff or file.name.startswith('_MEI')


def cleanup_tmp() -> None:
    logger.info('Preparing to cleanup tmp directory')
    tmp_dir = Path('/tmp/').glob('*')
    cache_cutoff = datetime.now(tz=UTC) - timedelta(hours=6)
    cutoff_epoch = int(cache_cutoff.strftime('%s'))
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


def load_config_from_file() -> dict[str, Any] | None:
    config_file = Path('/config/rotki_config.json')
    if not config_file.exists():
        logger.info('no config file provided')
        return None

    with open(config_file, encoding='utf-8') as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError as e:
            logger.error(e)
            return None
        else:
            return data


def load_config_from_env() -> dict[str, Any]:
    loglevel = os.environ.get('LOGLEVEL')
    logfromothermodules = os.environ.get('LOGFROMOTHERMODDULES')
    max_size_in_mb_all_logs = os.environ.get('MAX_SIZE_IN_MB_ALL_LOGS')
    max_logfiles_num = os.environ.get('MAX_LOGFILES_NUM')
    sqlite_instructions = os.environ.get('SQLITE_INSTRUCTIONS')

    return {
        'loglevel': loglevel,
        'logfromothermodules': logfromothermodules,
        'max_logfiles_num': max_logfiles_num,
        'max_size_in_mb_all_logs': max_size_in_mb_all_logs,
        'sqlite_instructions': sqlite_instructions,
    }


def load_config() -> list[str]:
    env_config = load_config_from_env()
    file_config = load_config_from_file()

    logger.info('loading config from env')

    loglevel = env_config.get('loglevel')
    log_from_other_modules = env_config.get('logfromothermodules')
    max_logfiles_num = env_config.get('max_logfiles_num')
    max_size_in_mb_all_logs = env_config.get('max_size_in_mb_all_logs')
    sqlite_instructions = env_config.get('sqlite_instructions')

    if file_config is not None:
        logger.info('loading config from file')

        if file_config.get('loglevel') is not None:
            loglevel = file_config.get('loglevel')

        if file_config.get('logfromothermodules') is not None:
            log_from_other_modules = file_config.get('logfromothermodules')

        if file_config.get('max_logfiles_num') is not None:
            max_logfiles_num = file_config.get('max_logfiles_num')

        if file_config.get('max_size_in_mb_all_logs') is not None:
            max_size_in_mb_all_logs = file_config.get('max_size_in_mb_all_logs')

        if file_config.get('sqlite_instructions') is not None:
            sqlite_instructions = file_config.get('sqlite_instructions')

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

    if max_logfiles_num is not None:
        args.extend(('--max-logfiles-num', int(max_logfiles_num)))

    if max_size_in_mb_all_logs is not None:
        args.extend(('--max-size-in-mb-all-logs', int(max_size_in_mb_all_logs)))

    if sqlite_instructions is not None:
        args.extend(('--sqlite-instructions', int(sqlite_instructions)))
    return args


cleanup_tmp()

# start colibri first and then start rotki
colibri = subprocess.Popen(['/usr/sbin/colibri'])
if colibri.returncode == 1:
    logger.error('Failed to start colibri')
    sys.exit(1)

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
    sys.exit(1)

logger.info('starting nginx')

nginx = subprocess.Popen('nginx -g "daemon off;"', shell=True)

if nginx.returncode == 1:
    logger.error('Failed to start nginx')
    sys.exit(1)


def terminate_process(process_name: str, process: subprocess.Popen) -> None:
    logger.info(f'Terminating {process_name}')
    if process.poll() is not None:
        logger.error(f'{process_name} was not running. This means that some error occurred.')
        sys.exit(1)

    process.terminate()
    process.wait()  # wait untill the process terminates


def graceful_exit(received_signal: int, _frame: FrameType | None) -> None:
    logger.info(f'Received signal {received_signal}. Exiting gracefully')
    terminate_process('rotki', rotki)
    terminate_process('nginx', nginx)
    sys.exit(0)


# Handle exits via ctrl+c or via `docker stop` gracefully
signal(SIGINT, graceful_exit)
signal(SIGTERM, graceful_exit)
signal(SIGQUIT, graceful_exit)


while True:
    time.sleep(60)

    if rotki.poll() is not None:
        logger.error('rotki has terminated exiting')
        sys.exit(1)

    if nginx.poll() is not None:
        logger.error('nginx was not running')
        sys.exit(1)

    logger.info('OK: processes still running')
