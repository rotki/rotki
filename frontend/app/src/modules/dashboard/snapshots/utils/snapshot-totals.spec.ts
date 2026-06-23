import { describe, expect, it } from 'vitest';
import { BalanceType } from '@/modules/balances/types/balances';
import { type BalanceSnapshot, BalanceSnapshotSchema, type LocationDataSnapshot, LocationDataSnapshotSchema } from '@/modules/dashboard/snapshots';
import {
  assetsTotal,
  getTotalEntry,
  getTotalValue,
  locationsTotal,
  nftsTotal,
  signedUsdValue,
  TOTAL_LOCATION,
} from '@/modules/dashboard/snapshots/utils/snapshot-totals';

interface BalanceOptions {
  usdValue: string;
  category?: BalanceType;
  assetIdentifier?: string;
  amount?: string;
}

function balance(options: BalanceOptions): BalanceSnapshot {
  return BalanceSnapshotSchema.parse({
    amount: options.amount ?? '1',
    assetIdentifier: options.assetIdentifier ?? 'ETH',
    category: options.category ?? BalanceType.ASSET,
    timestamp: 1700000000,
    usdValue: options.usdValue,
  });
}

function location(loc: string, usdValue: string): LocationDataSnapshot {
  return LocationDataSnapshotSchema.parse({ location: loc, timestamp: 1700000000, usdValue });
}

describe('modules/dashboard/snapshots/utils/snapshot-totals', () => {
  it('should add assets and subtract liabilities in signedUsdValue', () => {
    expect(signedUsdValue(balance({ category: BalanceType.ASSET, usdValue: '100' })).toNumber()).toBe(100);
    expect(signedUsdValue(balance({ category: BalanceType.LIABILITY, usdValue: '30' })).toNumber()).toBe(-30);
  });

  it('should net assets against liabilities in assetsTotal', () => {
    const snapshot = [
      balance({ category: BalanceType.ASSET, usdValue: '100' }),
      balance({ category: BalanceType.ASSET, usdValue: '50' }),
      balance({ category: BalanceType.LIABILITY, usdValue: '30' }),
    ];
    expect(assetsTotal(snapshot).toNumber()).toBe(120);
  });

  it('should return zero from assetsTotal for an empty snapshot', () => {
    expect(assetsTotal([]).toNumber()).toBe(0);
  });

  it('should only count NFT balances in nftsTotal', () => {
    const snapshot = [
      balance({ assetIdentifier: 'ETH', usdValue: '100' }),
      balance({ assetIdentifier: '_nft_0xabc_1', usdValue: '40' }),
      balance({ assetIdentifier: '_nft_0xabc_2', category: BalanceType.LIABILITY, usdValue: '10' }),
    ];
    expect(nftsTotal(snapshot).toNumber()).toBe(30);
  });

  it('should sum only non-total rows in locationsTotal', () => {
    const rows = [
      location('blockchain', '70'),
      location('kraken', '50'),
      location(TOTAL_LOCATION, '120'),
    ];
    expect(locationsTotal(rows).toNumber()).toBe(120);
  });

  it('should find the total entry and read its value', () => {
    const rows = [location('kraken', '50'), location(TOTAL_LOCATION, '120')];
    expect(getTotalEntry(rows)?.usdValue.toNumber()).toBe(120);
    expect(getTotalValue(rows).toNumber()).toBe(120);
  });

  it('should return zero from getTotalValue when there is no total row', () => {
    expect(getTotalValue([location('kraken', '50')]).toNumber()).toBe(0);
    expect(getTotalEntry([location('kraken', '50')])).toBeUndefined();
  });
});
