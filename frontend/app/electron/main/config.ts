import type { Writeable } from '@rotki/common';
import type { BackendOptions } from '@shared/ipc';
import fs from 'node:fs';
import { LogLevel } from '@shared/log-level';

const CONFIG_FILE = 'rotki_config.json';

const LOGLEVEL = 'loglevel';
const LOGDIR = 'log-dir';
const DATA_DIR = 'data-dir';
const LOG_FROM_OTHER_MODULES = 'logfromothermodules';
const MAX_LOG_SIZE = 'max_size_in_mb_all_logs';
const MAX_LOG_NUMBER = 'max_logfiles_num';
const SQLITE_INSTRUCTIONS = 'sqlite_instructions';

export function loadConfig(): Partial<BackendOptions> {
  const options: Writeable<Partial<BackendOptions>> = {};
  const filePath = CONFIG_FILE;
  const configExists = fs.existsSync(filePath);
  if (!configExists)
    return options;

  try {
    const configFile = fs.readFileSync(filePath);
    const config = JSON.parse(configFile.toString());

    if (LOGLEVEL in config) {
      const configLogLevel = config[LOGLEVEL];
      if (Object.values(LogLevel).includes(configLogLevel))
        options.loglevel = configLogLevel;
    }

    if (LOG_FROM_OTHER_MODULES in config)
      options.logFromOtherModules = config[LOG_FROM_OTHER_MODULES] === true;

    if (LOGDIR in config)
      options.logDirectory = config[LOGDIR];

    if (DATA_DIR in config)
      options.dataDirectory = config[DATA_DIR];

    if (MAX_LOG_SIZE in config)
      options.maxSizeInMbAllLogs = Number.parseInt(config[MAX_LOG_SIZE]);

    if (MAX_LOG_NUMBER in config)
      options.maxLogfilesNum = Number.parseInt(config[MAX_LOG_NUMBER]);

    if (SQLITE_INSTRUCTIONS in config)
      options.sqliteInstructions = Number.parseInt(config[SQLITE_INSTRUCTIONS]);

    return options;
  }
  catch {
    return options;
  }
}
