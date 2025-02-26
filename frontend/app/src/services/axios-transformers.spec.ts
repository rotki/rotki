import { describe, expect, it } from 'vitest';
import { camelCaseTransformer, noRootCamelCaseTransformer, snakeCaseTransformer } from '@/services/axios-transformers';

describe('axios transformers', () => {
  it('transform json to camelCase', () => {
    const json = '{"amount":"10","test_label":"label","data":[{"amount":"2","usd_value":"10"}]}';
    const parsed = JSON.parse(json);
    expect(camelCaseTransformer(parsed)).toMatchObject({
      amount: '10',
      data: [{ amount: '2', usdValue: '10' }],
      testLabel: 'label',
    });
  });

  it('transform object to snake_case', () => {
    const object = {
      data: [{ usdValue: bigNumberify(10) }, { usdValue: bigNumberify(11) }],
      label: 'test',
    };

    expect(JSON.stringify(snakeCaseTransformer(object))).toMatch(
      '{"data":[{"usd_value":"10"},{"usd_value":"11"}],"label":"test"}',
    );
  });

  it('transform capital to snake_case', () => {
    const object = {
      BTC: 2,
      ETH: 1,
    };

    expect(snakeCaseTransformer(object)).toMatchObject(JSON.parse('{"ETH":1,"BTC":2}'));
  });

  it('transformer no root', () => {
    const json = '{"_amount_": { "a_cbc": "1", "a_abc": "2"}}';
    const parsed = JSON.parse(json);
    const transformed = noRootCamelCaseTransformer(parsed);
    expect(transformed).toMatchObject({
      _amount_: {
        aAbc: '2',
        aCbc: '1',
      },
    });
  });
});
