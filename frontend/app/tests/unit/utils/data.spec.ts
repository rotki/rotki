import { expect } from 'vitest';
import { nonNullProperties } from '@/utils/data';

describe('utils/data', () => {
  test('returns a partial object without the null properties', async () => {
    const object = {
      a: 1,
      b: null,
      c: '442'
    };

    expect(nonNullProperties(object)).toStrictEqual({
      a: 1,
      c: '442'
    });
  });

  test('returns a partial object without empty arrays', () => {
    const a = {
      a: [],
      b: 2
    };

    expect(nonNullProperties(a)).toStrictEqual({
      b: 2
    });
  });

  test('returns partial in nested setup', () => {
    expect(
      nonNullProperties({
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
      nonNullProperties({
        a: {
          b: [],
          c: null,
          d: ['a', 'b']
        }
      })
    ).toStrictEqual({ a: { d: ['a', 'b'] } });
  });
});
