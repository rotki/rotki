import consola, { type ConsolaInstance, type LogLevel as ConsolaLogLevel, LogLevels, type LogObject } from 'consola';
import { LogLevel } from '@shared/log-level';
import { checkIfDevelopment } from '@shared/utils';
import { IndexedDb } from '@/utils/indexed-db';

const isDevelopment = checkIfDevelopment();

export function getDefaultLogLevel(): LogLevel {
  return isDevelopment ? LogLevel.DEBUG : LogLevel.CRITICAL;
}

export function getDefaultFrontendLogLevel(): ConsolaLogLevel {
  return isDevelopment ? LogLevels.debug : LogLevels.silent;
}

const mapping = {
  [LogLevel.CRITICAL]: LogLevels.silent,
  [LogLevel.ERROR]: LogLevels.error,
  [LogLevel.WARNING]: LogLevels.warn,
  [LogLevel.INFO]: LogLevels.info,
  [LogLevel.DEBUG]: LogLevels.debug,
  [LogLevel.TRACE]: LogLevels.trace,
};

export function mapToFrontendLogLevel(logLevel?: LogLevel): ConsolaLogLevel {
  if (!logLevel)
    return getDefaultFrontendLogLevel();

  return mapping[logLevel] ?? getDefaultLogLevel();
}

consola.level = getDefaultFrontendLogLevel();

function getMessage(logObj: LogObject): string {
  const type = logObj.type === 'log' ? '' : logObj.type;
  const tag = logObj.tag || '';
  const badge = tag ? `${type}: ${tag}` : type;

  return `${logObj.date.toLocaleString()} :: ${badge} :: ${logObj.args.join(' ')}`;
}

// We only need the indexed db in production.
// In development the plugin messes the line number from where the logs originated
if (!isDevelopment) {
  const { isPackaged, logToFile } = useInterop();

  if (isPackaged) {
    consola.addReporter({
      log(logObj) {
        logToFile(getMessage(logObj));
      },
    });
  }
  else {
    const loggerDb = new IndexedDb('db', 1, 'logs');
    consola.addReporter({
      log(logObj) {
        loggerDb.add({
          message: getMessage(logObj),
        });
      },
    });
  }
}

function setLevel(level?: LogLevel): void {
  consola.level = mapToFrontendLogLevel(level);
}

function loggerWithTag(tag: string): ConsolaInstance {
  return consola.withTag(tag);
}

export { consola as logger, loggerWithTag, setLevel };
