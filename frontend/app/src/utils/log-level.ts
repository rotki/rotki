export const TRACE = 'trace';
export const DEBUG = 'debug';
export const INFO = 'info';
export const WARN = 'warn';
export const ERROR = 'error';
export const SILENT = 'silent';
export const CRITICAL = 'critical';

export const levels = [
  TRACE,
  DEBUG,
  INFO,
  WARN,
  ERROR,
  SILENT,
  CRITICAL
] as const;

export type Level = typeof levels[number];
export const LOG_LEVEL = 'log_level';
