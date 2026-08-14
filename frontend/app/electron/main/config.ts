import type { Writeable } from '@rotki/common';
import type { BackendOptions } from '@shared/ipc';
import fs from 'node:fs';
import process from 'node:process';
import { LogLevel } from '@shared/log-level';

const CONFIG_FILE = 'rotki_config.json';

/**
 * Dev only: the data directory `pnpm dev --instance` allocated for this run.
 *
 * `scripts/dev/services.ts` hands the electron child the instance's four ports and this directory.
 * The ports were read (see `application.ts`) but the directory was not, so an instance run isolated
 * its ports and then opened the *shared* data directory anyway — taking its lock and failing to
 * start whenever another rotki was already running.
 *
 * It wins over the config file: an instance exists precisely so as not to touch the shared data.
 */
const INSTANCE_DATA_DIR_ENV = 'ROTKI_INSTANCE_DATA_DIR';

const LOGLEVEL = 'loglevel';
const LOGDIR = 'log-dir';
const DATA_DIR = 'data-dir';
const LOG_FROM_OTHER_MODULES = 'logfromothermodules';
const MAX_LOG_SIZE = 'max_size_in_mb_all_logs';
const MAX_LOG_NUMBER = 'max_logfiles_num';
const SQLITE_INSTRUCTIONS = 'sqlite_instructions';

// `config` is an untrusted JSON blob; each field is validated/coerced the same
// way the caller always has, so the values are read as `any` by design.
function applyConfig(config: Record<string, any>, options: Writeable<Partial<BackendOptions>>): void {
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
}

function applyInstanceDataDir(options: Writeable<Partial<BackendOptions>>): void {
  const dataDirectory = process.env[INSTANCE_DATA_DIR_ENV];
  if (dataDirectory)
    options.dataDirectory = dataDirectory;
}

export function loadConfig(): Partial<BackendOptions> {
  const options: Writeable<Partial<BackendOptions>> = {};
  const filePath = CONFIG_FILE;

  if (fs.existsSync(filePath)) {
    try {
      const configFile = fs.readFileSync(filePath);
      const config = JSON.parse(configFile.toString());
      applyConfig(config, options);
    }
    catch {
      // An unreadable or malformed config is ignored, as it always has been — but the instance
      // override below still has to run, or a broken config file would silently put an instance
      // back on the shared data directory.
    }
  }

  applyInstanceDataDir(options);
  return options;
}
