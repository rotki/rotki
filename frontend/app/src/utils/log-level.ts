export const DEBUG = 'debug';
export const INFO = 'info';
export const WARN = 'warn';
export const ERROR = 'error';
export const CRITICAL = 'critical';

export const levels = [DEBUG, INFO, WARN, ERROR, CRITICAL] as const;

export type Level = typeof levels[number];
export const LOG_LEVEL = 'log_level';
