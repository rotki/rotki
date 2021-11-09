import {
  axiosCamelCaseTransformer,
  axiosNoRootCamelCaseTransformer,
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

  test('transform capital to snake_case', async () => {
    const object = {
      ETH: 1,
      BTC: 2
    };

    expect(JSON.stringify(axiosSnakeCaseTransformer(object))).toMatch(
      '{"ETH":1,"BTC":2}'
    );
  });

  test('null keys transformer converts all numeric keys', () => {
    const json = '{"amount":"10","test_label":"1","data":[{"amount":"2"}]}';
    const parsed = setupJsonTransformer(null)(json);
    expect(axiosCamelCaseTransformer(parsed)).toMatchObject({
      amount: bigNumberify(10),
      testLabel: bigNumberify(1),
      data: [{ amount: bigNumberify(2) }]
    });
  });

  test('empty array transformer converts nothing', () => {
    const json = '{"amount":"10","test_label":"1","data":[{"amount":"2"}]}';
    const parsed = setupJsonTransformer([])(json);
    expect(axiosCamelCaseTransformer(parsed)).toMatchObject({
      amount: '10',
      testLabel: '1',
      data: [{ amount: '2' }]
    });
  });

  test('transformer can handle scientific notation', () => {
    const transformer = setupJsonTransformer(['amount']);
    expect(
      axiosCamelCaseTransformer(transformer('{"amount":"0E-27"}'))
    ).toMatchObject({
      amount: bigNumberify('0E-27')
    });
    expect(
      axiosCamelCaseTransformer(transformer('{"amount":"1E+2"}'))
    ).toMatchObject({
      amount: bigNumberify('1E+2')
    });
    expect(
      axiosCamelCaseTransformer(transformer('{"amount":"2.1E+2"}'))
    ).toMatchObject({
      amount: bigNumberify('2.1E+2')
    });
    expect(
      axiosCamelCaseTransformer(transformer('{"amount":"2.1e+2"}'))
    ).toMatchObject({
      amount: bigNumberify('2.1e+2')
    });
    expect(
      axiosCamelCaseTransformer(transformer('{"amount":"5.2211e+2"}'))
    ).toMatchObject({
      amount: bigNumberify('5.2211e+2')
    });
  });

  test('transformer supports numeric subkeys', () => {
    const json = '{"amount": { "ABC": "1", "BCD": "2"}}';
    const parsed = setupJsonTransformer(['amount'])(json);
    expect(axiosCamelCaseTransformer(parsed)).toMatchObject({
      amount: {
        ABC: bigNumberify(1),
        BCD: bigNumberify(2)
      }
    });
  });

  test('transformer no root', () => {
    const json = '{"_amount_": { "a_cbc": "1", "a_abc": "2"}}';
    const parsed = setupJsonTransformer([])(json);
    const transformed = axiosNoRootCamelCaseTransformer(parsed);
    expect(transformed).toMatchObject({
      _amount_: {
        aCbc: '1',
        aAbc: '2'
      }
    });
  });
});
