import { describe, expect, it } from 'vitest';
import { parseDateQuery, parseRangeQuery, type ParseTimestamp } from '@/modules/core/table/pill/core/typed-filters';

// Stands in for the app's date reading: `DD/MM/YYYY`, with the wire value being the unix second.
const parse: ParseTimestamp = (value: string): string | undefined => {
  const match = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value);
  if (!match)
    return undefined;
  const [, day, month, year] = match;
  return String(Date.UTC(Number(year), Number(month) - 1, Number(day)) / 1000);
};

const JAN_15 = '1705276800';
const JAN_20 = '1705708800';

describe('parseRangeQuery', () => {
  it('should read an explicit comparison as the one bound it names', () => {
    expect(parseRangeQuery('>100')).toStrictEqual([{ op: 'gt', range: { min: '100' }, values: [] }]);
    expect(parseRangeQuery('>= 1.5')).toStrictEqual([{ op: 'gt', range: { min: '1.5' }, values: [] }]);
    expect(parseRangeQuery('<50')).toStrictEqual([{ op: 'lt', range: { max: '50' }, values: [] }]);
    expect(parseRangeQuery('=< 50')).toStrictEqual([{ op: 'lt', range: { max: '50' }, values: [] }]);
  });

  it('should read a span as both bounds', () => {
    const between = [{ op: 'between', range: { max: '50', min: '10' }, values: [] }];
    expect(parseRangeQuery('10-50')).toStrictEqual(between);
    expect(parseRangeQuery('10 .. 50')).toStrictEqual(between);
    expect(parseRangeQuery('10 to 50')).toStrictEqual(between);
  });

  // The editor refuses a maximum below its minimum, so a reversed span would otherwise offer a
  // filter that cannot be applied.
  it('should order a span written backwards', () => {
    expect(parseRangeQuery('50-10')).toStrictEqual([{ op: 'between', range: { max: '50', min: '10' }, values: [] }]);
  });

  // A bare number cannot say which bound is meant, and guessing would be wrong half the time.
  it('should offer both directions for a bare number', () => {
    expect(parseRangeQuery('100')).toStrictEqual([
      { op: 'gt', range: { min: '100' }, values: [] },
      { op: 'lt', range: { max: '100' }, values: [] },
    ]);
  });

  it('should offer nothing for what is not an amount', () => {
    expect(parseRangeQuery('uniswap')).toStrictEqual([]);
    expect(parseRangeQuery('15/01/2024')).toStrictEqual([]);
    expect(parseRangeQuery('0x1234')).toStrictEqual([]);
    expect(parseRangeQuery('')).toStrictEqual([]);
  });
});

describe('parseDateQuery', () => {
  it('should read a written date as both directions', () => {
    expect(parseDateQuery('15/01/2024', parse)).toStrictEqual([
      { date: { from: JAN_15 }, op: 'after', values: [] },
      { date: { to: JAN_15 }, op: 'before', values: [] },
    ]);
  });

  it('should read a prefix as the one direction it names', () => {
    expect(parseDateQuery('>15/01/2024', parse)).toStrictEqual([{ date: { from: JAN_15 }, op: 'after', values: [] }]);
    expect(parseDateQuery('after 15/01/2024', parse)).toStrictEqual([{ date: { from: JAN_15 }, op: 'after', values: [] }]);
    expect(parseDateQuery('< 15/01/2024', parse)).toStrictEqual([{ date: { to: JAN_15 }, op: 'before', values: [] }]);
    expect(parseDateQuery('until 15/01/2024', parse)).toStrictEqual([{ date: { to: JAN_15 }, op: 'before', values: [] }]);
  });

  it('should read a spaced span as both bounds', () => {
    expect(parseDateQuery('15/01/2024 - 20/01/2024', parse)).toStrictEqual([
      { date: { from: JAN_15, to: JAN_20 }, op: 'between', values: [] },
    ]);
  });

  // A number is an amount, not a year or half a date: the injected parser is lenient enough to read
  // `1.5` as a day and a month, so the shape is checked before it is ever asked.
  it('should not read a number as a date', () => {
    expect(parseDateQuery('100', parse)).toStrictEqual([]);
    expect(parseDateQuery('2024', parse)).toStrictEqual([]);
    expect(parseDateQuery('1.5', parse)).toStrictEqual([]);
    expect(parseDateQuery('>100', parse)).toStrictEqual([]);
  });

  // Whether a well-shaped date is a real one is the injected parser's call, since only it knows the
  // user's format; refusing it has to mean no row rather than a row holding nothing.
  it('should offer nothing when the parser rejects the date', () => {
    expect(parseDateQuery('15/01/2024', () => undefined)).toStrictEqual([]);
    expect(parseDateQuery('15/01/2024 - 20/01/2024', () => undefined)).toStrictEqual([]);
    expect(parseDateQuery('uniswap', parse)).toStrictEqual([]);
  });

  // A date already carries separators, so a span has to be spaced to be told apart from one date.
  it('should not split a single hyphenated date', () => {
    expect(parseDateQuery('15-01-2024', parse)).toStrictEqual([]);
  });
});
