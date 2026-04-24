import { LogLevel } from '@shared/log-level';

export function resolveLogLevel(loglevel: LogLevel | undefined, isDev: boolean): LogLevel {
  return loglevel ?? (isDev ? LogLevel.DEBUG : LogLevel.CRITICAL);
}
