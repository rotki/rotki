import {
  axiosCamelCaseTransformer,
  axiosSnakeCaseTransformer,
  setupJsonTransformer
} from '@/services/axios-tranformers';
import { bigNumberify } from '@/utils/bignumbers';

describe('axios transformers', () => {
  test('transform json to camelCase', async () => {
    const json = '{"amount":"10","test_label":"label","data":[{"amount":"2"}]}';
    const parsed = setupJsonTransformer(['amount'])(json);
    expect(axiosCamelCaseTransformer(parsed)).toMatchObject({
      amount: bigNumberify(10),
      testLabel: 'label',
      data: [{ amount: bigNumberify(2) }]
    });
  });

  test('transform object to snake_case', async () => {
    const object = {
      data: [{ usdValue: bigNumberify(10) }, { usdValue: bigNumberify(11) }],
      label: 'test'
    };

    expect(JSON.stringify(axiosSnakeCaseTransformer(object))).toMatch(
      '{"data":[{"usd_value":"10"},{"usd_value":"11"}],"label":"test"}'
    );
  });
});
