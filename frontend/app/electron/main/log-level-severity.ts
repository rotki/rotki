import { LogLevel } from '@shared/log-level';

const SEVERITY: Record<LogLevel, number> = {
  [LogLevel.TRACE]: 0,
  [LogLevel.DEBUG]: 1,
  [LogLevel.INFO]: 2,
  [LogLevel.WARNING]: 3,
  [LogLevel.ERROR]: 4,
  [LogLevel.CRITICAL]: 5,
};

export function isLogLevelActive(level: LogLevel, threshold: LogLevel): boolean {
  return SEVERITY[level] >= SEVERITY[threshold];
}
