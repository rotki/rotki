import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { BalanceType } from '@/modules/balances/types/balances';
import { type BalanceSnapshot, BalanceSnapshotSchema, type LocationDataSnapshot, LocationDataSnapshotSchema, type Snapshot } from '@/modules/dashboard/snapshots';
import { TOTAL_LOCATION } from '@/modules/dashboard/snapshots/utils/snapshot-totals';
import { getSnapshotWarnings } from '@/modules/dashboard/snapshots/utils/snapshot-warnings';

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

function snapshot(balances: BalanceSnapshot[], locations: LocationDataSnapshot[] = []): Snapshot {
  return { balancesSnapshot: balances, locationDataSnapshot: locations };
}

describe('modules/dashboard/snapshots/utils/snapshot-warnings', () => {
  it('should return no warnings for a clean snapshot', () => {
    const clean = snapshot(
      [balance({ assetIdentifier: 'ETH', usdValue: '100' })],
      [location(TOTAL_LOCATION, '100')],
    );
    expect(getSnapshotWarnings(clean)).toEqual([]);
  });

  it('should flag a negative amount or negative value', () => {
    const result = getSnapshotWarnings(snapshot([
      balance({ amount: '-1', assetIdentifier: 'ETH', usdValue: '100' }),
      balance({ assetIdentifier: 'BTC', usdValue: '-5' }),
    ]));
    expect(result).toEqual([
      { asset: 'ETH', balanceIndex: 0, code: 'negative-balance' },
      { asset: 'BTC', balanceIndex: 1, code: 'negative-balance' },
    ]);
  });

  it('should flag a zero-value row', () => {
    const result = getSnapshotWarnings(snapshot([balance({ assetIdentifier: 'ETH', usdValue: '0' })]));
    expect(result).toEqual([{ asset: 'ETH', balanceIndex: 0, code: 'zero-value' }]);
  });

  it('should not flag a zero-value spam asset', () => {
    const result = getSnapshotWarnings(
      snapshot([
        balance({ assetIdentifier: 'SPAM', usdValue: '0' }),
        balance({ assetIdentifier: 'ETH', usdValue: '0' }),
      ]),
      { isSpam: (identifier): boolean => identifier === 'SPAM' },
    );
    expect(result).toEqual([{ asset: 'ETH', balanceIndex: 1, code: 'zero-value' }]);
  });

  it('should flag a duplicated asset once on its first occurrence', () => {
    const result = getSnapshotWarnings(snapshot([
      balance({ assetIdentifier: 'ETH', usdValue: '100' }),
      balance({ assetIdentifier: 'BTC', usdValue: '50' }),
      balance({ assetIdentifier: 'ETH', usdValue: '20' }),
    ]));
    expect(result).toEqual([{ asset: 'ETH', balanceIndex: 0, code: 'duplicate-asset' }]);
  });

  it('should not flag the same asset held as both an asset and a liability', () => {
    const result = getSnapshotWarnings(snapshot([
      balance({ assetIdentifier: 'ETH', category: BalanceType.ASSET, usdValue: '100' }),
      balance({ assetIdentifier: 'ETH', category: BalanceType.LIABILITY, usdValue: '20' }),
    ]));
    expect(result).toEqual([]);
  });

  it('should flag an NFT whose amount is not one', () => {
    const result = getSnapshotWarnings(snapshot([
      balance({ amount: '2', assetIdentifier: '_nft_0xabc_1', usdValue: '40' }),
      balance({ amount: '1', assetIdentifier: '_nft_0xabc_2', usdValue: '10' }),
    ]));
    expect(result).toEqual([{ asset: '_nft_0xabc_1', balanceIndex: 0, code: 'nft-amount' }]);
  });

  it('should flag a net-worth swing beyond the threshold', () => {
    const current = snapshot([balance({ usdValue: '200' })], [location(TOTAL_LOCATION, '200')]);
    const result = getSnapshotWarnings(current, { previousTotal: bigNumberify('100') });
    expect(result).toEqual([{ code: 'net-worth-swing', swingPercent: 100 }]);
  });

  it('should not flag a net-worth swing within the threshold', () => {
    const current = snapshot([balance({ usdValue: '120' })], [location(TOTAL_LOCATION, '120')]);
    expect(getSnapshotWarnings(current, { previousTotal: bigNumberify('100') })).toEqual([]);
  });

  it('should skip the swing check when there is no previous total or it is zero', () => {
    const current = snapshot([balance({ usdValue: '200' })], [location(TOTAL_LOCATION, '200')]);
    expect(getSnapshotWarnings(current)).toEqual([]);
    expect(getSnapshotWarnings(current, { previousTotal: bigNumberify('0') })).toEqual([]);
  });

  it('should honour a custom swing threshold', () => {
    const current = snapshot([balance({ usdValue: '130' })], [location(TOTAL_LOCATION, '130')]);
    expect(getSnapshotWarnings(current, { previousTotal: bigNumberify('100'), swingThreshold: 0.2 }))
      .toEqual([{ code: 'net-worth-swing', swingPercent: 30 }]);
  });
});
