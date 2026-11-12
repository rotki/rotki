import { type AssetBalanceWithPriceAndChains, bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { compareByAsset, withQueriedOnlyAssets } from '@/modules/balances/view/history-comparison';

function row(asset: string, amount: number, price = 2): AssetBalanceWithPriceAndChains {
  return { amount: bigNumberify(amount), asset, price: bigNumberify(price), value: bigNumberify(amount * price) };
}

describe('withQueriedOnlyAssets', () => {
  it('should list an asset only the queried side holds at zero, at its queried price', () => {
    const rows = withQueriedOnlyAssets([row('ETH', 15)], [row('ETH', 25), row('BTC', 1.5, 72000)]);

    expect(rows.map(({ amount, asset, price, value }) => [asset, amount.toNumber(), price.toNumber(), value.toNumber()]))
      .toStrictEqual([['ETH', 15, 2, 30], ['BTC', 0, 72000, 0]]);
  });

  it('should leave out a queried-only asset worth nothing', () => {
    const rows = withQueriedOnlyAssets([row('ETH', 15)], [row('ETH', 25), row('SPAM', 1000000, 0)]);

    expect(rows.map(({ asset }) => asset)).toStrictEqual(['ETH']);
  });

  it('should keep the history row when both sides hold the asset', () => {
    const history = [row('ETH', 15)];

    expect(withQueriedOnlyAssets(history, [row('ETH', 25)])).toStrictEqual(history);
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
