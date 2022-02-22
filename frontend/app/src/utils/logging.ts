import * as log from 'loglevel';
import { LogLevelNumbers } from 'loglevel';
import { interop } from '@/electron-interop';
import IndexedDb from '@/utils/indexed-db';
import { LogLevel } from '@/utils/log-level';

const logger = require('loglevel');
const isDevelopment = process.env.NODE_ENV === 'development';

export const getDefaultLogLevel = () => {
  return isDevelopment ? LogLevel.DEBUG : LogLevel.CRITICAL;
};

export const getDefaultFrontendLogLevel = () => {
  return isDevelopment ? log.levels.DEBUG : log.levels.SILENT;
};

const mapping = {
  [LogLevel.CRITICAL]: log.levels.SILENT,
  [LogLevel.ERROR]: log.levels.ERROR,
  [LogLevel.WARNING]: log.levels.WARN,
  [LogLevel.INFO]: log.levels.INFO,
  [LogLevel.DEBUG]: log.levels.DEBUG
};

export const mapToFrontendLogLevel = (logLevel?: LogLevel) => {
  if (!logLevel) {
    return getDefaultFrontendLogLevel();
  }
  return mapping[logLevel] ?? getDefaultLogLevel();
};
logger.setDefaultLevel(getDefaultFrontendLogLevel());

const loggerDb = new IndexedDb('db', 1, 'logs');

// write log in log file everytime logger called
const originalFactory = logger.methodFactory;
logger.methodFactory = function (
  methodName: string,
  logLevel: LogLevelNumbers,
  loggerName: string | symbol
) {
  const rawMethod = originalFactory(methodName, logLevel, loggerName);

  return (...message: any[]) => {
    rawMethod(message.join(''));

    if (
      loggerName !== 'console-only' &&
      Object.values(LogLevel).indexOf(methodName as LogLevel) >= logLevel
    ) {
      if (interop.isPackaged) {
        interop.logToFile(`(${methodName}): ${message.join('')}`);
      } else {
        loggerDb.add({
          message: `${new Date(Date.now()).toISOString()}: ${message.join('')}`
        });
      }
    }
  };
};

logger.setLevel(logger.getLevel());

const setLevel = (loglevel?: LogLevel, persist: boolean = true) => {
  logger.setLevel(mapToFrontendLogLevel(loglevel), persist);
};

export { logger, setLevel };
