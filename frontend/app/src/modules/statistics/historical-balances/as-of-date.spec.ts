import dayjs from 'dayjs';
import { describe, expect, it } from 'vitest';
import { AsOfPreset, asOfTimestamp, parseDateKey, presetDateKey, toDateKey } from './as-of-date';

const NOON_2026_03_15 = dayjs('2026-03-15T12:00:00').unix();

describe('parseDateKey', () => {
  it('should accept a real calendar day', () => {
    expect(parseDateKey('2024-12-31')).toBe('2024-12-31');
  });

  it.each([
    ['a day that does not exist', '2024-02-30'],
    ['a timestamp', '1700000000'],
    ['a date with a time', '2024-12-31T10:00'],
    ['a repeated query value', ['2024-12-31', '2024-12-30']],
    ['nothing', undefined],
  ])('should reject %s', (_, value) => {
    expect(parseDateKey(value)).toBeUndefined();
  });
});

describe('asOfTimestamp', () => {
  it('should stand a past day for its last second', () => {
    const at = asOfTimestamp('2024-12-31', NOON_2026_03_15);

    expect(dayjs.unix(at).format('YYYY-MM-DD HH:mm:ss')).toBe('2024-12-31 23:59:59');
  });

  it('should stand today for now, since the rest of today has not happened', () => {
    expect(asOfTimestamp('2026-03-15', NOON_2026_03_15)).toBe(NOON_2026_03_15);
  });

  it('should round-trip through the day it names', () => {
    expect(toDateKey(asOfTimestamp('2024-06-01', NOON_2026_03_15))).toBe('2024-06-01');
  });
});

describe('presetDateKey', () => {
  it.each([
    [AsOfPreset.TODAY, '2026-03-15'],
    [AsOfPreset.END_OF_LAST_YEAR, '2025-12-31'],
    [AsOfPreset.END_OF_YEAR_BEFORE, '2024-12-31'],
  ])('should name %s as %s', (preset, day) => {
    expect(presetDateKey(preset, NOON_2026_03_15)).toBe(day);
  });
});
