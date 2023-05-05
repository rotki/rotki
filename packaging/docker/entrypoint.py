#!/usr/bin/python3
import json
import logging
import os
import shutil
from signal import signal, SIGINT, SIGTERM, SIGQUIT
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


def load_config() -> List[str]:
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
        args.append('--max-logfiles-num')
        args.append(int(max_logfiles_num))

    if max_size_in_mb_all_logs is not None:
        args.append('--max-size-in-mb-all-logs')
        args.append(int(max_size_in_mb_all_logs))

    if sqlite_instructions is not None:
        args.append('--sqlite-instructions')
        args.append(int(sqlite_instructions))
    return args


cleanup_tmp()

# start colibri first and then start rotki
colibri = subprocess.Popen(['/usr/sbin/colibri'])
if colibri.returncode == 1:
    logger.error('Failed to start colibri')
    exit(1)

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


def terminate_process(process_name: str, process: subprocess.Popen) -> None:
    logger.info(f'Terminating {process_name}')
    if process.poll() is not None:
        logger.error(f'{process_name} was not running. This means that some error occurred.')
        exit(1)

    process.terminate()
    process.wait()  # wait untill the process terminates


def graceful_exit(signal, frame):
    logger.info(f'Received signal {signal}. Exiting gracefully')
    terminate_process('rotki', rotki)
    terminate_process('nginx', nginx)
    exit(0)


# Handle exits via ctrl+c or via `docker stop` gracefully
signal(SIGINT, graceful_exit)
signal(SIGTERM, graceful_exit)
signal(SIGQUIT, graceful_exit)


while True:
    time.sleep(60)

    if rotki.poll() is not None:
        logger.error('rotki has terminated exiting')
        exit(1)

    if nginx.poll() is not None:
        logger.error('nginx was not running')
        exit(1)

    logger.info('OK: processes still running')
