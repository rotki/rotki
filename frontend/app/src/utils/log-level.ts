export const DEBUG = 'debug';
export const INFO = 'info';
export const WARN = 'warn';
export const ERROR = 'error';
export const CRITICAL = 'critical';

export const levels = [DEBUG, INFO, WARN, ERROR, CRITICAL] as const;

export type Level = typeof levels[number];

export function currentLogLevel(): Level {
  const item = localStorage.getItem(LOG_LEVEL) as any;
  if (item && levels.includes(item)) {
    return item as Level;
  }
  return process.env.NODE_ENV === 'development' ? DEBUG : CRITICAL;
}

export const LOG_LEVEL = 'log_level';
