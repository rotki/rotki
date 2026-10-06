import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { rankOwnedAssets } from '@/modules/premium/rank-owned-assets';

function balance(asset: string, value: number): { asset: string; value: ReturnType<typeof bigNumberify> } {
  return { asset, value: bigNumberify(value) };
}

describe('rankOwnedAssets', () => {
  it('should put held assets first, largest value first', () => {
    const ranked = rankOwnedAssets(['SPAM', 'BTC', 'ETH', 'USDC'], [
      balance('ETH', 3000),
      balance('USDC', 50),
      balance('BTC', 60000),
    ]);

    expect(ranked).toStrictEqual(['BTC', 'ETH', 'USDC', 'SPAM']);
  });

  it('should keep assets without a current balance in their incoming order', () => {
    const ranked = rankOwnedAssets(['C', 'A', 'ETH', 'B'], [balance('ETH', 1)]);

    expect(ranked).toStrictEqual(['ETH', 'C', 'A', 'B']);
  });

  it('should offer only owned assets, not every balance', () => {
    const ranked = rankOwnedAssets(['ETH'], [balance('BTC', 60000), balance('ETH', 1)]);

    expect(ranked).toStrictEqual(['ETH']);
  });
});
