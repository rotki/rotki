import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { nonEmptyOr, nonEmptyProperties, toRem } from '@/modules/core/common/data/data';

describe('data-utils', () => {
  it('should return a partial object without the null properties', () => {
    const object = {
      a: 1,
      b: null,
      c: '442',
    };

    expect(nonEmptyProperties(object)).toStrictEqual({
      a: 1,
      c: '442',
    });
  });

  it('should return a partial object without empty arrays', () => {
    const a = {
      a: [],
      b: 2,
    };

    expect(nonEmptyProperties(a)).toStrictEqual({
      b: 2,
    });
  });

  it('should return partial in nested setup', () => {
    expect(
      nonEmptyProperties({
        a: {
          b: [],
          c: null,
          d: '',
        },
      }),
    ).toStrictEqual({ a: { d: '' } });
  });

  it('should properly handle arrays', () => {
    expect(
      nonEmptyProperties({
        a: {
          b: [],
          c: null,
          d: ['a', 'b'],
        },
      }),
    ).toStrictEqual({ a: { d: ['a', 'b'] } });
  });

  it('should not transform BigNumber', () => {
    const number = bigNumberify(10);
    expect(
      nonEmptyProperties({
        a: {
          number,
        },
      }),
    ).toStrictEqual({ a: { number } });
  });

  it('should also remove empty strings', () => {
    expect(
      nonEmptyProperties({
        a: '',
        b: 'test',
        c: 123,
        d: [],
      }, {
        removeEmptyString: true,
      }),
    ).toStrictEqual({ b: 'test', c: 123 });
  });

  it('should work with alwaysPickKeys option', () => {
    expect(
      nonEmptyProperties({
        a: '',
        b: 'test',
        c: 123,
        d: [],
      }, {
        alwaysPickKeys: ['a', 'd'],
      }),
    ).toStrictEqual({ a: '', b: 'test', c: 123, d: [] });
  });

  it('should convert values to rems', () => {
    expect(toRem('10px')).toBe('0.625rem');
    expect(toRem('10')).toBe('10rem');
    expect(toRem(10)).toBe('10rem');
    expect(toRem('10rem')).toBe('10rem');
    expect(toRem('10%')).toBe('10%');
    expect(toRem('auto')).toBe('auto');
  });

  describe('nonEmptyOr', () => {
    it('should return the value when it is a non-empty string', () => {
      expect(nonEmptyOr('value', 'fallback')).toBe('value');
    });

    it('should return the fallback for an empty string', () => {
      expect(nonEmptyOr('', 'fallback')).toBe('fallback');
    });

    it('should return the fallback for nullish values', () => {
      expect(nonEmptyOr(undefined, 'fallback')).toBe('fallback');
      expect(nonEmptyOr(null, 'fallback')).toBe('fallback');
    });

    it('should support a non-string fallback', () => {
      expect(nonEmptyOr('', null)).toBeNull();
      expect(nonEmptyOr('kept', null)).toBe('kept');
    });
  });
});
