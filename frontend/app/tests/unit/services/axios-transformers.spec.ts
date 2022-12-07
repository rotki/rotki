import {
  axiosCamelCaseTransformer,
  axiosNoRootCamelCaseTransformer,
  axiosSnakeCaseTransformer
} from '@/services/axios-tranformers';
import { bigNumberify } from '@/utils/bignumbers';

describe('axios transformers', () => {
  test('transform json to camelCase', async () => {
    const json =
      '{"amount":"10","test_label":"label","data":[{"amount":"2","usd_value":"10"}]}';
    const parsed = JSON.parse(json);
    expect(axiosCamelCaseTransformer(parsed)).toMatchObject({
      amount: '10',
      testLabel: 'label',
      data: [{ amount: '2', usdValue: '10' }]
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

  test('transform capital to snake_case', async () => {
    const object = {
      ETH: 1,
      BTC: 2
    };

    expect(JSON.stringify(axiosSnakeCaseTransformer(object))).toMatch(
      '{"ETH":1,"BTC":2}'
    );
  });

  test('transformer no root', () => {
    const json = '{"_amount_": { "a_cbc": "1", "a_abc": "2"}}';
    const parsed = JSON.parse(json);
    const transformed = axiosNoRootCamelCaseTransformer(parsed);
    expect(transformed).toMatchObject({
      _amount_: {
        aCbc: '1',
        aAbc: '2'
      }
    });
  });
});
