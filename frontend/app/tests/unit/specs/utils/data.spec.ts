import { nonEmptyProperties, toRem } from '@/utils/data';
import { describe, expect, it } from 'vitest';

describe('utils/data', () => {
  it('returns a partial object without the null properties', () => {
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

  it('returns a partial object without empty arrays', () => {
    const a = {
      a: [],
      b: 2,
    };

    expect(nonEmptyProperties(a)).toStrictEqual({
      b: 2,
    });
  });

  it('returns partial in nested setup', () => {
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

  it('properly handles arrays', () => {
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

  it('do not transform BigNumber', () => {
    const number = bigNumberify(10);
    expect(
      nonEmptyProperties({
        a: {
          number,
        },
      }),
    ).toStrictEqual({ a: { number } });
  });

  it('also remove empty strings', () => {
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

  it('alwaysPickKeys option works', () => {
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

  it('convert values to rems', () => {
    expect(toRem('10px')).toStrictEqual('0.625rem');
    expect(toRem('10')).toStrictEqual('10rem');
    expect(toRem(10)).toStrictEqual('10rem');
    expect(toRem('10rem')).toStrictEqual('10rem');
    expect(toRem('10%')).toStrictEqual('10%');
    expect(toRem('auto')).toStrictEqual('auto');
  });
});
