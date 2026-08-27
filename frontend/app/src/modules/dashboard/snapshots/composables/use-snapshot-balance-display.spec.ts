import type { Snapshot } from '@/modules/dashboard/snapshots';
import { bigNumberify } from '@rotki/common';
import { describe, expect, it } from 'vitest';
import { BalanceType } from '@/modules/balances/types/balances';
import { useSnapshotBalanceDisplay } from '@/modules/dashboard/snapshots/composables/use-snapshot-balance-display';

const TS = 1_600_000_000;

function balance(
  assetIdentifier: string,
  usdValue: number,
  category: BalanceType = BalanceType.ASSET,
  amount = 1,
): Snapshot['balancesSnapshot'][number] {
  return { amount: bigNumberify(amount), assetIdentifier, category, timestamp: TS, usdValue: bigNumberify(usdValue) };
}

function createSnapshot(): Snapshot {
  return {
    balancesSnapshot: [
      balance('ETH', 100),
      balance('DAI', 30, BalanceType.LIABILITY),
      // An nft whose amount is not 1: a genuine row-level warning.
      balance('_nft_0xabc_1', 40, BalanceType.ASSET, 2),
      balance('USDC', 0),
    ],
    locationDataSnapshot: [
      { location: 'kraken', timestamp: TS, usdValue: bigNumberify(170) },
      { location: 'total', timestamp: TS, usdValue: bigNumberify(170) },
    ],
  };
}

describe('useSnapshotBalanceDisplay', () => {
  it('should index each row so an edit can name the one it came from', () => {
    const { data } = useSnapshotBalanceDisplay(createSnapshot());

    expect(get(data).map(item => item.index)).toStrictEqual([0, 1, 2, 3]);
  });

  it('should mark an nft row in its category label, which the wire category does not', () => {
    const { data } = useSnapshotBalanceDisplay(createSnapshot());
    const [eth, , nft] = get(data);

    expect(eth.categoryLabel).toBe(BalanceType.ASSET);
    expect(nft.categoryLabel).toContain('dashboard.snapshot.detail.balances.nft');
  });

  it('should flag the row a sanity warning names', () => {
    const { warningsByIndex } = useSnapshotBalanceDisplay(createSnapshot());

    expect(get(warningsByIndex).has(2)).toBe(true);
  });

  it('should not flag zero-value rows', () => {
    const { warningsByIndex } = useSnapshotBalanceDisplay(createSnapshot());

    expect(get(warningsByIndex).has(3)).toBe(false);
  });

  it('should total the snapshot from its location data', () => {
    const { total } = useSnapshotBalanceDisplay(createSnapshot());

    expect(get(total).toNumber()).toBe(170);
  });

  it('should share an asset positively and a liability negatively', () => {
    const { data, sharePercent } = useSnapshotBalanceDisplay(createSnapshot());
    const [eth, dai] = get(data);

    expect(sharePercent(eth)).toBe('58.82');
    expect(sharePercent(dai)).toBe('-17.65');
  });

  it('should give no share when net worth is not positive, the ratio being meaningless against it', () => {
    const snapshot = createSnapshot();
    snapshot.locationDataSnapshot = [{ location: 'total', timestamp: TS, usdValue: bigNumberify(0) }];
    const { data, sharePercent } = useSnapshotBalanceDisplay(snapshot);

    expect(sharePercent(get(data)[0])).toBe('');
  });

  it('should colour a liability, an nft and a plain asset apart', () => {
    const { categoryChipColor, data } = useSnapshotBalanceDisplay(createSnapshot());
    const [eth, dai, nft] = get(data);

    expect(categoryChipColor(dai)).toBe('error');
    expect(categoryChipColor(nft)).toBe('info');
    expect(categoryChipColor(eth)).toBe('grey');
  });

  it('should tell rows apart by liability and by nft', () => {
    const { data, isLiability, isNftRow } = useSnapshotBalanceDisplay(createSnapshot());
    const [eth, dai, nft] = get(data);

    expect(isLiability(dai)).toBe(true);
    expect(isLiability(eth)).toBe(false);
    expect(isNftRow(nft)).toBe(true);
    expect(isNftRow(eth)).toBe(false);
  });

  it('should describe each row-level warning code', () => {
    const { describeWarning } = useSnapshotBalanceDisplay(createSnapshot());

    expect(describeWarning({ balanceIndex: 0, code: 'negative-balance' }))
      .toBe('dashboard.snapshot.detail.balances.flag_reasons.negative');
    expect(describeWarning({ balanceIndex: 0, code: 'duplicate-asset' }))
      .toBe('dashboard.snapshot.detail.balances.flag_reasons.duplicate');
    expect(describeWarning({ balanceIndex: 0, code: 'nft-amount' }))
      .toBe('dashboard.snapshot.detail.balances.flag_reasons.nft_amount');
  });
});
