import { describe, expect, it } from 'vitest';
import {
  looksLikeDateQuery,
  looksLikeRangeQuery,
  parseDateQuery,
  parseRangeQuery,
  type ParseTimestamp,
} from '@/modules/core/table/pill/core/typed-filters';

/** Stands in for the app's date reading: accepts `DD/MM/YYYY`, returns the unix second. */
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

  it('should read a written lower bound, in the wording the bar labels its own rows with', () => {
    const gt = [{ op: 'gt', range: { min: '100' }, values: [] }];
    expect(parseRangeQuery('over 100')).toStrictEqual(gt);
    expect(parseRangeQuery('above 100')).toStrictEqual(gt);
    expect(parseRangeQuery('more than 100')).toStrictEqual(gt);
    expect(parseRangeQuery('greater than 100')).toStrictEqual(gt);
    expect(parseRangeQuery('at least 100')).toStrictEqual(gt);
    expect(parseRangeQuery('bigger 100')).toStrictEqual(gt);
  });

  it('should read a written upper bound', () => {
    const lt = [{ op: 'lt', range: { max: '50' }, values: [] }];
    expect(parseRangeQuery('under 50')).toStrictEqual(lt);
    expect(parseRangeQuery('below 50')).toStrictEqual(lt);
    expect(parseRangeQuery('less than 50')).toStrictEqual(lt);
    expect(parseRangeQuery('smaller than 50')).toStrictEqual(lt);
    expect(parseRangeQuery('at most 50')).toStrictEqual(lt);
    expect(parseRangeQuery('up to 50')).toStrictEqual(lt);
  });

  it('should read a written bound whatever its casing', () => {
    expect(parseRangeQuery('Over 100')).toStrictEqual([{ op: 'gt', range: { min: '100' }, values: [] }]);
    expect(parseRangeQuery('LESS THAN 50')).toStrictEqual([{ op: 'lt', range: { max: '50' }, values: [] }]);
  });

  it('should keep a span with a `to` separator a span, telling it from the `to` of `up to`', () => {
    expect(parseRangeQuery('10 to 50')).toStrictEqual([{ op: 'between', range: { max: '50', min: '10' }, values: [] }]);
    expect(parseRangeQuery('up to 50')).toStrictEqual([{ op: 'lt', range: { max: '50' }, values: [] }]);
  });

  it('should offer nothing for a word with no number after it', () => {
    expect(parseRangeQuery('over')).toStrictEqual([]);
    expect(parseRangeQuery('less than')).toStrictEqual([]);
    expect(parseRangeQuery('overflow')).toStrictEqual([]);
  });

  it('should read a span as both bounds', () => {
    const between = [{ op: 'between', range: { max: '50', min: '10' }, values: [] }];
    expect(parseRangeQuery('10-50')).toStrictEqual(between);
    expect(parseRangeQuery('10 .. 50')).toStrictEqual(between);
    expect(parseRangeQuery('10 to 50')).toStrictEqual(between);
  });

  it('should order a span written backwards, the editor refusing a maximum below its minimum', () => {
    expect(parseRangeQuery('50-10')).toStrictEqual([{ op: 'between', range: { max: '50', min: '10' }, values: [] }]);
  });

  it('should offer both directions for a bare number, which names no bound of its own', () => {
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

  it('should not read a number as a date, however leniently the injected parser reads one', () => {
    expect(parseDateQuery('100', parse)).toStrictEqual([]);
    expect(parseDateQuery('2024', parse)).toStrictEqual([]);
    expect(parseDateQuery('1.5', parse)).toStrictEqual([]);
    expect(parseDateQuery('>100', parse)).toStrictEqual([]);
  });

  it('should offer nothing when the parser rejects the date, only it knowing the user\'s format', () => {
    expect(parseDateQuery('15/01/2024', () => undefined)).toStrictEqual([]);
    expect(parseDateQuery('15/01/2024 - 20/01/2024', () => undefined)).toStrictEqual([]);
    expect(parseDateQuery('uniswap', parse)).toStrictEqual([]);
  });

  it('should not split a single hyphenated date, a span having to be spaced to be told apart', () => {
    expect(parseDateQuery('15-01-2024', parse)).toStrictEqual([]);
  });
});

describe('looksLikeDateQuery', () => {
  it('should claim an operator word with nothing after it yet', () => {
    expect(looksLikeDateQuery('after')).toBe(true);
    expect(looksLikeDateQuery('before ')).toBe(true);
    expect(looksLikeDateQuery('since 15/')).toBe(true);
    expect(looksLikeDateQuery('UNTIL')).toBe(true);
  });

  it('should claim a date that is still being written', () => {
    expect(looksLikeDateQuery('15/')).toBe(true);
    expect(looksLikeDateQuery('15/01')).toBe(true);
    expect(looksLikeDateQuery('15/01/20')).toBe(true);
    expect(looksLikeDateQuery('15.')).toBe(true);
    expect(looksLikeDateQuery('15.01.')).toBe(true);
    expect(looksLikeDateQuery('15-01-2024')).toBe(true);
  });

  it('should claim a span whose second bound is missing', () => {
    expect(looksLikeDateQuery('15/01/2024 -')).toBe(true);
    expect(looksLikeDateQuery('15/01/2024 to')).toBe(true);
  });

  it('should claim a bare comparison marker, which the amount fields claim as well', () => {
    expect(looksLikeDateQuery('>')).toBe(true);
    expect(looksLikeDateQuery('<=')).toBe(true);
  });

  it('should leave an amount to the amount fields, a separator between digits never being half a date', () => {
    expect(looksLikeDateQuery('100')).toBe(false);
    expect(looksLikeDateQuery('>100')).toBe(false);
    expect(looksLikeDateQuery('10 - 50')).toBe(false);
    expect(looksLikeDateQuery('10-50')).toBe(false);
    expect(looksLikeDateQuery('1.5')).toBe(false);
  });

  it('should claim nothing for text that is not heading anywhere', () => {
    expect(looksLikeDateQuery('')).toBe(false);
    expect(looksLikeDateQuery('   ')).toBe(false);
    expect(looksLikeDateQuery('uniswap')).toBe(false);
  });

  it('should not claim a word that merely ends in a span separator, which has to sit between bounds', () => {
    expect(looksLikeDateQuery('auto')).toBe(false);
    expect(looksLikeDateQuery('photo')).toBe(false);
    expect(looksLikeDateQuery('uniswap -')).toBe(false);
  });
});

describe('looksLikeRangeQuery', () => {
  it('should claim a number being written, with or without a marker', () => {
    expect(looksLikeRangeQuery('100')).toBe(true);
    expect(looksLikeRangeQuery('1.')).toBe(true);
    expect(looksLikeRangeQuery('>')).toBe(true);
    expect(looksLikeRangeQuery('>= 1.5')).toBe(true);
  });

  it('should claim a span whose second bound is missing', () => {
    expect(looksLikeRangeQuery('10 -')).toBe(true);
    expect(looksLikeRangeQuery('10 to')).toBe(true);
    expect(looksLikeRangeQuery('10 ..')).toBe(true);
  });

  it('should claim a written bound with nothing after it yet', () => {
    expect(looksLikeRangeQuery('over')).toBe(true);
    expect(looksLikeRangeQuery('less than')).toBe(true);
    expect(looksLikeRangeQuery('at')).toBe(true);
    expect(looksLikeRangeQuery('UNDER')).toBe(true);
  });

  it('should leave a date to the date fields', () => {
    expect(looksLikeRangeQuery('15/01')).toBe(false);
    expect(looksLikeRangeQuery('after')).toBe(false);
    expect(looksLikeRangeQuery('15/01/2024')).toBe(false);
  });

  it('should claim nothing for text that is not heading anywhere', () => {
    expect(looksLikeRangeQuery('')).toBe(false);
    expect(looksLikeRangeQuery('uniswap')).toBe(false);
  });

  it('should not claim a longer word that merely starts with a bound word, which matches whole', () => {
    expect(looksLikeRangeQuery('overflow')).toBe(false);
    expect(looksLikeRangeQuery('underlying')).toBe(false);
    expect(looksLikeRangeQuery('atomic')).toBe(false);
    expect(looksLikeRangeQuery('uphold')).toBe(false);
  });
});
