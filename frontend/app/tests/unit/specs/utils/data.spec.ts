import { expect } from 'vitest';

describe('utils/data', () => {
  test('returns a partial object without the null properties', async () => {
    const object = {
      a: 1,
      b: null,
      c: '442'
    };

    expect(nonEmptyProperties(object)).toStrictEqual({
      a: 1,
      c: '442'
    });
  });

  test('returns a partial object without empty arrays', () => {
    const a = {
      a: [],
      b: 2
    };

    expect(nonEmptyProperties(a)).toStrictEqual({
      b: 2
    });
  });

  test('returns partial in nested setup', () => {
    expect(
      nonEmptyProperties({
        a: {
          b: [],
          c: null,
          d: ''
        }
      })
    ).toStrictEqual({ a: { d: '' } });
  });

  test('properly handles arrays', () => {
    expect(
      nonEmptyProperties({
        a: {
          b: [],
          c: null,
          d: ['a', 'b']
        }
      })
    ).toStrictEqual({ a: { d: ['a', 'b'] } });
  });

  test('do not transform BigNumber', () => {
    const number = bigNumberify(10);
    expect(
      nonEmptyProperties({
        a: {
          number
        }
      })
    ).toStrictEqual({ a: { number } });
  });

  test('convert values to rems', () => {
    expect(toRem('10px')).toStrictEqual('0.625rem');
    expect(toRem('10')).toStrictEqual('10rem');
    expect(toRem(10)).toStrictEqual('10rem');
    expect(toRem('10rem')).toStrictEqual('10rem');
    expect(toRem('10%')).toStrictEqual('10%');
    expect(toRem('auto')).toStrictEqual('auto');
  });
});
