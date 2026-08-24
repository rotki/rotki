import { describe, expect, it } from 'vitest';
import {
  checkSetting,
  timeRangeHoursSchema,
  tolerancePercentageSchema,
} from '@/modules/history/events/asset-movement-matching-settings';

const messages = {
  timeRangeMin: 'time_range_min',
  toleranceMax: 'tolerance_max',
  toleranceMin: 'tolerance_min',
};

function tolerance(value: string): string[] {
  return checkSetting(tolerancePercentageSchema(messages), value);
}

function timeRange(value: string): string[] {
  return checkSetting(timeRangeHoursSchema(messages), value);
}

describe('tolerancePercentageSchema', () => {
  it.each([
    ['5'],
    ['0.0001'],
    ['100'],
  ])('should accept %s percent', (value) => {
    expect(tolerance(value)).toEqual([]);
  });

  it('should reject more than all of the amount', () => {
    expect(tolerance('100.1')).toEqual(['tolerance_max']);
  });

  it.each([
    ['0'],
    ['0.00001'],
    ['-1'],
  ])('should reject %s as too small', (value) => {
    expect(tolerance(value)).toEqual(['tolerance_min']);
  });
});

describe('timeRangeHoursSchema', () => {
  it.each([
    ['1'],
    ['24'],
  ])('should accept %s hours', (value) => {
    expect(timeRange(value)).toEqual([]);
  });

  it.each([
    ['0'],
    ['0.5'],
  ])('should reject %s hours', (value) => {
    expect(timeRange(value)).toEqual(['time_range_min']);
  });
});

describe('checkSetting', () => {
  it.each([
    [''],
    ['   '],
  ])('should leave a field holding %s alone', (value) => {
    // The menu writes on every keystroke, and an emptied field is on its way somewhere rather than
    // wrong. The old rules only ever reported a value out of range.
    expect(tolerance(value)).toEqual([]);
    expect(timeRange(value)).toEqual([]);
  });

  it('should say nothing about text that is not a number', () => {
    expect(tolerance('abc')).toEqual([]);
  });
});
