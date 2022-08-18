import logger, { LogLevelNumbers } from 'loglevel';
import { interop } from '@/electron-interop';
import { checkIfDevelopment } from '@/utils/env-utils';
import IndexedDb from '@/utils/indexed-db';
import { LogLevel } from '@/utils/log-level';

const isDevelopment = checkIfDevelopment();

export const getDefaultLogLevel = () => {
  return isDevelopment ? LogLevel.DEBUG : LogLevel.CRITICAL;
};

export const getDefaultFrontendLogLevel = () => {
  return isDevelopment ? logger.levels.DEBUG : logger.levels.SILENT;
};

const mapping = {
  [LogLevel.CRITICAL]: logger.levels.SILENT,
  [LogLevel.ERROR]: logger.levels.ERROR,
  [LogLevel.WARNING]: logger.levels.WARN,
  [LogLevel.INFO]: logger.levels.INFO,
  [LogLevel.DEBUG]: logger.levels.DEBUG,
  [LogLevel.TRACE]: logger.levels.TRACE
};

export const mapToFrontendLogLevel = (logLevel?: LogLevel) => {
  if (!logLevel) {
    return getDefaultFrontendLogLevel();
  }
  return mapping[logLevel] ?? getDefaultLogLevel();
};
logger.setDefaultLevel(getDefaultFrontendLogLevel());

// We only need the indexed db in production.
// In development the plugin messes the line number from where the logs originated
if (!isDevelopment) {
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
      rawMethod(...message);

      if (
        loggerName !== 'console-only' &&
        Object.values(LogLevel).indexOf(methodName as LogLevel) >= logLevel
      ) {
        if (interop.isPackaged) {
          interop.logToFile(`(${methodName}): ${message.join('')}`);
        } else {
          loggerDb.add({
            message: `${new Date(Date.now()).toISOString()}: ${message.join(
              ''
            )}`
          });
        }
      }
    };
  };
}

logger.setLevel(logger.getLevel());

const setLevel = (loglevel?: LogLevel, persist: boolean = true) => {
  logger.setLevel(mapToFrontendLogLevel(loglevel), persist);
};

export { logger, setLevel };
