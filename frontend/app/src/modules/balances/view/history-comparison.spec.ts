import { type AssetBalanceWithPriceAndChains, bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import {
  type AssetComparison,
  compareAsset,
  compareByAsset,
  mergeTopGaps,
  reconciliationAssetQuery,
  sumValues,
  withMissingAssets,
} from '@/modules/balances/view/history-comparison';

function row(asset: string, amount: number, price = 2): AssetBalanceWithPriceAndChains {
  return { amount: bigNumberify(amount), asset, price: bigNumberify(price), value: bigNumberify(amount * price) };
}

function comparison(delta: number, valueDelta: number, manual = 0): AssetComparison {
  return {
    delta: bigNumberify(delta),
    history: bigNumberify(0),
    manual: bigNumberify(manual),
    queried: bigNumberify(0),
    valueDelta: bigNumberify(valueDelta),
  };
}

describe('withMissingAssets', () => {
  it('should work in both directions, so each view lists the assets only the other holds', () => {
    const live = [row('ETH', 25)];
    const history = [row('ETH', 15), row('DAI', 500, 1)];

    expect(withMissingAssets(live, history).map(({ amount, asset }) => `${asset}:${amount.toFixed()}`)).toStrictEqual(['ETH:25', 'DAI:0']);
    expect(withMissingAssets(history, live).map(({ asset }) => asset)).toStrictEqual(['ETH', 'DAI']);
  });

  it('should list an asset only the queried side holds at zero, at its queried price', () => {
    const rows = withMissingAssets([row('ETH', 15)], [row('ETH', 25), row('BTC', 1.5, 72000)]);

    expect(rows.map(({ amount, asset, price, value }) => [asset, amount.toNumber(), price.toNumber(), value.toNumber()]))
      .toStrictEqual([['ETH', 15, 2, 30], ['BTC', 0, 72000, 0]]);
  });

  it('should leave out a queried-only asset worth nothing', () => {
    const rows = withMissingAssets([row('ETH', 15)], [row('ETH', 25), row('SPAM', 1000000, 0)]);

    expect(rows.map(({ asset }) => asset)).toStrictEqual(['ETH']);
  });

  it('should keep the history row when both sides hold the asset', () => {
    const history = [row('ETH', 15)];

    expect(withMissingAssets(history, [row('ETH', 25)])).toStrictEqual(history);
  });
});

describe('compareByAsset', () => {
  it('should report history minus queried, and the manual amount behind the gap', () => {
    const comparison = compareByAsset([row('ETH', 15)], [row('ETH', 25)], [row('ETH', 3)]).get('ETH');

    expect(comparison?.delta.toNumber()).toBe(-10);
    expect(comparison?.manual.toNumber()).toBe(3);
    expect(comparison?.queried.toNumber()).toBe(25);
    expect(comparison?.history.toNumber()).toBe(15);
  });

  it('should compare an asset only history holds against zero', () => {
    const comparison = compareByAsset([row('DAI', 500)], [], []).get('DAI');

    expect(comparison?.delta.toNumber()).toBe(500);
    expect(comparison?.manual.isZero()).toBe(true);
  });

  it('should compare an asset only the queried side holds against zero', () => {
    const comparison = compareByAsset([], [row('BTC', 1.5)], [row('BTC', 1.5)]).get('BTC');

    expect(comparison?.delta.toNumber()).toBe(-1.5);
    expect(comparison?.manual.toNumber()).toBe(1.5);
  });
});

describe('compareAsset', () => {
  it('should compute the comparison for a single target asset', () => {
    const result = compareAsset('ETH', [row('ETH', 15, 100)], [row('ETH', 25, 100)], [row('ETH', 3, 100)]);

    expect(result?.delta.toNumber()).toBe(-10);
    expect(result?.valueDelta.toNumber()).toBe(-1000);
    expect(result?.manual.toNumber()).toBe(3);
  });

  it('should return undefined when neither view holds the target asset', () => {
    expect(compareAsset('SOL', [row('ETH', 15)], [row('BTC', 1)], [])).toBeUndefined();
  });
});

describe('sumValues', () => {
  it('should sum row values across the list', () => {
    expect(sumValues([row('ETH', 2, 2000), row('DAI', 500, 1)]).toNumber()).toBe(4500);
    expect(sumValues([]).isZero()).toBe(true);
  });
});

describe('mergeTopGaps', () => {
  it('should not let a zero-delta asset comparison shadow a non-zero liability gap for the same asset', () => {
    const gaps = mergeTopGaps(new Map([['DAI', comparison(0, 0)]]), new Map([['DAI', comparison(-500, -500)]]), 3);

    expect(gaps.map(([asset]) => asset)).toStrictEqual(['DAI']);
    expect(gaps[0][1].delta.toNumber()).toBe(-500);
  });

  it('should keep the larger absolute value delta when both asset and liability disagree for one asset', () => {
    const gaps = mergeTopGaps(new Map([['DAI', comparison(-10, -10)]]), new Map([['DAI', comparison(-500, -500)]]), 3);

    expect(gaps).toHaveLength(1);
    expect(gaps[0][1].valueDelta.toNumber()).toBe(-500);
  });

  it('should rank combined asset and liability gaps by absolute value delta up to the limit', () => {
    const gaps = mergeTopGaps(
      new Map([['BTC', comparison(-1, -50000)], ['SPAM', comparison(-1000000, -1)]]),
      new Map([['DEBT', comparison(-1000, -1000)], ['ETH', comparison(-5, -10000)]]),
      3,
    );

    expect(gaps.map(([asset]) => asset)).toStrictEqual(['BTC', 'ETH', 'DEBT']);
  });
});

describe('reconciliationAssetQuery', () => {
  it('should return the identifier for regular assets and the symbol for collection parents with an identifier fallback', () => {
    expect(reconciliationAssetQuery('eip155:1/erc20:0xA0b8', false, 'USDC')).toBe('eip155:1/erc20:0xA0b8');
    expect(reconciliationAssetQuery('eip155:1/erc20:0xA0b8', true, 'USDC')).toBe('USDC');
    expect(reconciliationAssetQuery('eip155:1/erc20:0xA0b8', true, '')).toBe('eip155:1/erc20:0xA0b8');
  });
});
