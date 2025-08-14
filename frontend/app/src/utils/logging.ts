import { LogLevel } from '@shared/log-level';
import { checkIfDevelopment, startPromise } from '@shared/utils';
import consola, { type LogLevel as ConsolaLogLevel, LogLevels, type LogObject } from 'consola';
import { useInterop } from '@/composables/electron-interop';
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
  [LogLevel.DEBUG]: LogLevels.debug,
  [LogLevel.ERROR]: LogLevels.error,
  [LogLevel.INFO]: LogLevels.info,
  [LogLevel.TRACE]: LogLevels.trace,
  [LogLevel.WARNING]: LogLevels.warn,
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

function getElectronMessage(logObj: LogObject): { level: LogLevel; message: string } {
  const levelMap = {
    debug: LogLevel.DEBUG,
    error: LogLevel.ERROR,
    fatal: LogLevel.CRITICAL,
    info: LogLevel.INFO,
    log: LogLevel.INFO,
    success: LogLevel.INFO,
    trace: LogLevel.TRACE,
    warn: LogLevel.WARNING,
    warning: LogLevel.WARNING,
  } as const;

  const level = levelMap[logObj.type as keyof typeof levelMap] ?? LogLevel.INFO;
  const tag = logObj.tag ? `[${logObj.tag}] ` : '';
  const message = `[vue] ${tag}${logObj.args.join(' ')}`;

  return { level, message };
}

// We only need the indexed db in production.
// In development the plugin messes the line number from where the logs originated
const { isPackaged, logToFile } = useInterop();

if (isPackaged) {
  consola.addReporter({
    log(logObj) {
      const { level, message } = getElectronMessage(logObj);
      logToFile(level, message);
    },
  });
}
else {
  const loggerDb = new IndexedDb('db', 1, 'logs');
  consola.addReporter({
    log(logObj): void {
      startPromise(loggerDb.add({
        message: getMessage(logObj),
      }));
    },
  });
}

function setLevel(level?: LogLevel): void {
  consola.level = mapToFrontendLogLevel(level);
}

export { consola as logger, setLevel };
