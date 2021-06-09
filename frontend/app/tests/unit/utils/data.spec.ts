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
});
