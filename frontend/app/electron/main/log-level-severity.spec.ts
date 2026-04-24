import { LogLevel } from '@shared/log-level';
import { describe, expect, it } from 'vitest';
import { isLogLevelActive } from './log-level-severity';

describe('isLogLevelActive', () => {
  it('should emit messages at or above the threshold', () => {
    expect(isLogLevelActive(LogLevel.ERROR, LogLevel.DEBUG)).toBe(true);
    expect(isLogLevelActive(LogLevel.CRITICAL, LogLevel.INFO)).toBe(true);
    expect(isLogLevelActive(LogLevel.DEBUG, LogLevel.DEBUG)).toBe(true);
  });

  it('should suppress messages below the threshold', () => {
    expect(isLogLevelActive(LogLevel.DEBUG, LogLevel.INFO)).toBe(false);
    expect(isLogLevelActive(LogLevel.INFO, LogLevel.WARNING)).toBe(false);
    expect(isLogLevelActive(LogLevel.TRACE, LogLevel.DEBUG)).toBe(false);
  });

  it('should let CRITICAL through when the threshold is DEBUG (regression #12079)', () => {
    // The previous string-based comparison returned false for
    // `'critical' >= 'debug'`, silently dropping critical errors whenever the
    // user switched the log level to debug.
    expect(isLogLevelActive(LogLevel.CRITICAL, LogLevel.DEBUG)).toBe(true);
    expect(isLogLevelActive(LogLevel.ERROR, LogLevel.WARNING)).toBe(true);
  });
});
