import type { BackendOptions } from '@shared/ipc';
import { LogLevel } from '@shared/log-level';
import { assert, describe, expect, it } from 'vitest';
import {
  backendDefaultsState,
  backendNumericSchema,
  type BackendOptionsFormFields,
  diffBackendOptions,
  hasBackendOptionChanges,
  parseValue,
  stringifyValue,
  toBackendOptions,
} from '@/modules/settings/backend/backend-options-form';

function fields(overrides: Partial<BackendOptionsFormFields> = {}): BackendOptionsFormFields {
  return {
    dataDirectory: '/data',
    logDirectory: '/logs',
    logFromOtherModules: false,
    loglevel: LogLevel.DEBUG,
    maxLogFiles: '3',
    maxLogSize: '300',
    sqliteInstructions: '5000',
    ...overrides,
  };
}

const initial: Partial<BackendOptions> = {
  dataDirectory: '/data',
  logDirectory: '/logs',
  logFromOtherModules: false,
  loglevel: LogLevel.DEBUG,
  maxLogfilesNum: 3,
  maxSizeInMbAllLogs: 300,
  sqliteInstructions: 5000,
};

describe('parseValue', () => {
  it.each([
    ['', 0],
    ['0', 0],
    ['42', 42],
    // parseInt truncates rather than rejecting, which is why '1.5' is saved as 1.
    ['1.5', 1],
    ['1e5', 1],
    ['abc', 0],
    // parseInt does accept a sign, unlike the field's validation rule.
    ['-1', -1],
  ])('should parse %j as %i', (input, expected): void => {
    expect(parseValue(input)).toBe(expected);
  });

  it('should treat a missing value as zero', (): void => {
    expect(parseValue()).toBe(0);
  });
});

describe('stringifyValue', () => {
  it.each([
    [undefined, '0'],
    [0, '0'],
    [3, '3'],
  ])('should stringify %j as %j', (input, expected): void => {
    expect(stringifyValue(input)).toBe(expected);
  });
});

describe('toBackendOptions', () => {
  it('should project the raw fields onto the option shape', (): void => {
    expect(toBackendOptions(fields())).toEqual(initial);
  });

  it('should parse the three numeric fields', (): void => {
    expect(toBackendOptions(fields({ maxLogFiles: '', maxLogSize: '1.9', sqliteInstructions: 'x' }))).toMatchObject({
      maxLogfilesNum: 0,
      maxSizeInMbAllLogs: 1,
      sqliteInstructions: 0,
    });
  });
});

describe('diffBackendOptions', () => {
  it('should be empty when nothing changed', (): void => {
    expect(diffBackendOptions(fields(), initial)).toEqual({});
  });

  it('should carry only the changed fields', (): void => {
    expect(diffBackendOptions(fields({ maxLogSize: '301' }), initial)).toEqual({ maxSizeInMbAllLogs: 301 });
  });

  it.each([
    ['dataDirectory', { dataDirectory: '/other' }, { dataDirectory: '/other' }],
    ['logDirectory', { logDirectory: '/other-logs' }, { logDirectory: '/other-logs' }],
    ['logFromOtherModules', { logFromOtherModules: true }, { logFromOtherModules: true }],
    ['loglevel', { loglevel: LogLevel.WARNING }, { loglevel: LogLevel.WARNING }],
    ['maxLogFiles', { maxLogFiles: '4' }, { maxLogfilesNum: 4 }],
    ['sqliteInstructions', { sqliteInstructions: '5001' }, { sqliteInstructions: 5001 }],
  ] as const)('should report a changed %s', (_name, override, expected): void => {
    expect(diffBackendOptions(fields(override), initial)).toEqual(expected);
  });

  it('should report every field when there are no initial options', (): void => {
    expect(diffBackendOptions(fields(), {})).toEqual(initial);
  });

  // The two functions answer slightly different questions: the diff only looks
  // at the seven fields the form owns, while the changed check compares whole
  // objects. An initial option the form does not render therefore enables save
  // while contributing nothing to the payload.
  it('should ignore an initial option the form does not own', (): void => {
    const withExtra: Partial<BackendOptions> = { ...initial, sleepSeconds: 60 };

    expect(diffBackendOptions(fields(), withExtra)).toEqual({});
    expect(hasBackendOptionChanges(fields(), withExtra)).toBe(true);
  });
});

describe('hasBackendOptionChanges', () => {
  it('should be false when the fields match the initial options', (): void => {
    expect(hasBackendOptionChanges(fields(), initial)).toBe(false);
  });

  it('should be true for a changed field', (): void => {
    expect(hasBackendOptionChanges(fields({ logFromOtherModules: true }), initial)).toBe(true);
  });

  it('should be false when a numeric field changes only in formatting', (): void => {
    // Both parse to 300, so nothing is actually different.
    expect(hasBackendOptionChanges(fields({ maxLogSize: '300.4' }), initial)).toBe(false);
  });
});

describe('backendNumericSchema', () => {
  const messages = { min: 'min-0', nonEmpty: 'non-empty' };
  const schema = backendNumericSchema(messages);

  function messagesFor(value: string): string[] {
    const result = schema.safeParse({ maxLogFiles: '3', maxLogSize: value, sqliteInstructions: '5000' });
    if (result.success)
      return [];

    return result.error.issues.filter(issue => issue.path.join('.') === 'maxLogSize').map(issue => issue.message);
  }

  // The table measured from vuelidate's `and(numeric, minValue(0))` + `required`,
  // which this schema replaces. Every row, including the message order of the
  // last one, is the behaviour that shipped.
  it.each([
    ['0', []],
    ['300', []],
    // numeric allows a fractional part; parseValue truncates it on save.
    ['1.5', []],
    ['', ['non-empty']],
    ['-1', ['min-0']],
    ['+1', ['min-0']],
    ['1e5', ['min-0']],
    ['abc', ['min-0']],
    ['1.', ['min-0']],
    // Unreachable through a type="number" input, but vuelidate reported both
    // rules in this order: not digits, and empty once trimmed.
    ['  ', ['min-0', 'non-empty']],
  ])('should report %j as %j', (value, expected): void => {
    expect(messagesFor(value)).toEqual(expected);
  });

  it('should apply the same rule to all three fields', (): void => {
    const result = schema.safeParse({ maxLogFiles: '-1', maxLogSize: '', sqliteInstructions: '5000' });
    assert(!result.success);

    expect(result.error.issues.map(issue => [issue.path.join('.'), issue.message])).toEqual([
      ['maxLogFiles', 'min-0'],
      ['maxLogSize', 'non-empty'],
    ]);
  });
});

describe('backendDefaultsState', () => {
  const defaults = { maxLogfilesNum: 3, maxSizeInMbAllLogs: 300, sqliteInstructions: 5000 };

  it('should report every field at its default', (): void => {
    expect(backendDefaultsState(fields(), defaults)).toEqual({
      maxLogFiles: true,
      maxLogSize: true,
      sqliteInstructions: true,
    });
  });

  it('should report only the field that moved off its default', (): void => {
    expect(backendDefaultsState(fields({ maxLogFiles: '4' }), defaults)).toEqual({
      maxLogFiles: false,
      maxLogSize: true,
      sqliteInstructions: true,
    });
  });

  it('should compare the parsed value, not the string', (): void => {
    expect(backendDefaultsState(fields({ maxLogSize: '300.9' }), defaults).maxLogSize).toBe(true);
  });
});
