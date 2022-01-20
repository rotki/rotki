import { LogLevelNumbers } from 'loglevel';
import { interop } from '@/electron-interop';
import { DEBUG, Level, levels } from '@/utils/log-level';
const logger = require('loglevel');

if (process.env.NODE_ENV === 'development') {
  logger.setDefaultLevel(DEBUG);
}

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

    if (levels.indexOf(methodName as Level) >= logLevel) {
      if (interop.isPackaged) {
        interop.logToFile(`(${methodName}): ${message.join('')}`);
      }
    }
  };
};

logger.setLevel(logger.getLevel());

export { logger };
