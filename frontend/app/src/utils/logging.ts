import logger, {
  type LogLevelNames,
  type LogLevelNumbers,
  type LoggingMethod
} from 'loglevel';
import IndexedDb from '@/utils/indexed-db';
import { LogLevel } from '@/utils/log-level';

const isDevelopment = checkIfDevelopment();

export const getDefaultLogLevel = (): LogLevel =>
  isDevelopment ? LogLevel.DEBUG : LogLevel.CRITICAL;

export const getDefaultFrontendLogLevel = (): LogLevelNumbers =>
  isDevelopment ? logger.levels.DEBUG : logger.levels.SILENT;

const mapping = {
  [LogLevel.CRITICAL]: logger.levels.SILENT,
  [LogLevel.ERROR]: logger.levels.ERROR,
  [LogLevel.WARNING]: logger.levels.WARN,
  [LogLevel.INFO]: logger.levels.INFO,
  [LogLevel.DEBUG]: logger.levels.DEBUG,
  [LogLevel.TRACE]: logger.levels.TRACE
};

export const mapToFrontendLogLevel = (logLevel?: LogLevel): LogLevelNumbers => {
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
    methodName: LogLevelNames,
    logLevel: LogLevelNumbers,
    loggerName: string | symbol
  ): LoggingMethod {
    const rawMethod = originalFactory(methodName, logLevel, loggerName);

    const { isPackaged, logToFile } = useInterop();

    return (...message: any[]): void => {
      rawMethod(...message);

      if (
        loggerName !== 'console-only' &&
        Object.values(LogLevel).indexOf(methodName as LogLevel) >= logLevel
      ) {
        if (isPackaged) {
          logToFile(`(${methodName}): ${message.join('')}`);
        } else {
          void loggerDb.add({
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

const setLevel = (loglevel?: LogLevel, persist = true): void => {
  logger.setLevel(mapToFrontendLogLevel(loglevel), persist);
};

export { logger, setLevel };
