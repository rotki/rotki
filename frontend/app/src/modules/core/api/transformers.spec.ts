import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { camelCaseTransformer, noRootCamelCaseTransformer, snakeCaseTransformer } from '@/modules/core/api/transformers';

describe('transformers', () => {
  it('should transform json to camelCase', () => {
    const json = '{"amount":"10","test_label":"label","data":[{"amount":"2","usd_value":"10"}]}';
    const parsed = JSON.parse(json);
    expect(camelCaseTransformer(parsed)).toEqual({
      amount: '10',
      data: [{ amount: '2', usdValue: '10' }],
      testLabel: 'label',
    });
  });

  it('should transform object to snake_case', () => {
    const object = {
      data: [{ usdValue: bigNumberify(10) }, { usdValue: bigNumberify(11) }],
      label: 'test',
    };

    expect(JSON.stringify(snakeCaseTransformer(object))).toMatch(
      '{"data":[{"usd_value":"10"},{"usd_value":"11"}],"label":"test"}',
    );
  });

  it('should transform capital to snake_case', () => {
    const object = {
      BTC: 2,
      ETH: 1,
    };

    expect(snakeCaseTransformer(object)).toEqual(JSON.parse('{"ETH":1,"BTC":2}'));
  });

  it('should skip nested transformation for specified keys', () => {
    const object = {
      asyncQuery: true,
      upToVersion: 5,
      conflicts: {
        someAssetId: 'local',
        anotherAssetId: 'remote',
      },
    };

    const result = snakeCaseTransformer(object, ['conflicts']);

    expect(result).toEqual({
      async_query: true,
      up_to_version: 5,
      conflicts: {
        someAssetId: 'local',
        anotherAssetId: 'remote',
      },
    });
  });

  it('should skip deeply nested content for specified keys', () => {
    const object = {
      conflictData: {
        levelOne: {
          levelTwo: 'value',
        },
      },
      normalData: {
        nestedKey: 'test',
      },
    };

    const result = snakeCaseTransformer(object, ['conflictData']);

    expect(result).toEqual({
      conflict_data: {
        levelOne: {
          levelTwo: 'value',
        },
      },
      normal_data: {
        nested_key: 'test',
      },
    });
  });

  it('should handle transformer with no root', () => {
    const json = '{"_amount_": { "a_cbc": "1", "a_abc": "2"}}';
    const parsed = JSON.parse(json);
    const transformed = noRootCamelCaseTransformer(parsed);
    expect(transformed).toEqual({
      _amount_: {
        aAbc: '2',
        aCbc: '1',
      },
    });
  });
});
