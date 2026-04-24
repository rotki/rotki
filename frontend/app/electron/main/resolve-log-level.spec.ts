import { LogLevel } from '@shared/log-level';
import { describe, expect, it } from 'vitest';
import { resolveLogLevel } from './resolve-log-level';

describe('resolveLogLevel', () => {
  it('should fall back to DEBUG in dev when no loglevel is provided', () => {
    expect(resolveLogLevel(undefined, true)).toBe(LogLevel.DEBUG);
  });

  it('should fall back to CRITICAL in production when no loglevel is provided', () => {
    // Matches the frontend default in getDefaultLogLevel() so both loggers
    // stay consistent when no explicit level has been persisted.
    expect(resolveLogLevel(undefined, false)).toBe(LogLevel.CRITICAL);
  });

  it('should honor the provided loglevel in production (regression #12079)', () => {
    // The inline ?? / ?: expression previously applied wrong precedence and
    // always returned DEBUG whenever any loglevel was supplied.
    expect(resolveLogLevel(LogLevel.CRITICAL, false)).toBe(LogLevel.CRITICAL);
    expect(resolveLogLevel(LogLevel.WARNING, false)).toBe(LogLevel.WARNING);
    expect(resolveLogLevel(LogLevel.ERROR, false)).toBe(LogLevel.ERROR);
  });

  it('should honor the provided loglevel in dev', () => {
    expect(resolveLogLevel(LogLevel.WARNING, true)).toBe(LogLevel.WARNING);
    expect(resolveLogLevel(LogLevel.CRITICAL, true)).toBe(LogLevel.CRITICAL);
  });
});
