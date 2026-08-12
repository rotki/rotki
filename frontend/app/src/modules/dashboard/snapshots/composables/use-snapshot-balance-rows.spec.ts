import { bigNumberify } from '@rotki/common';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { BalanceType } from '@/modules/balances/types/balances';
import { ZeroValueFilter } from '@/modules/dashboard/snapshots';
import { type Filters, SnapshotBalanceFilterKeys, SnapshotCategories } from '@/modules/dashboard/snapshots/composables/use-snapshot-balance-filter';
import { type IndexedBalanceSnapshot, useSnapshotBalanceRows } from '@/modules/dashboard/snapshots/composables/use-snapshot-balance-rows';

// Drive spam/ignored from per-test lists rather than resolving real asset info.
let spamIds: string[] = [];
let ignoredIds: string[] = [];
vi.mock('@/modules/dashboard/snapshots/composables/use-snapshot-asset-filters', () => ({
  useSnapshotAssetFilters: (): { isSpamAsset: (id: string) => boolean; isIgnoredAsset: (id: string) => boolean } => ({
    isIgnoredAsset: (id: string): boolean => ignoredIds.includes(id),
    isSpamAsset: (id: string): boolean => spamIds.includes(id),
  }),
}));

// The haystack reads symbol/name off the asset info; the identifier is enough to match on here.
vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): { getAssetField: (id: string, field: string) => string } => ({
    getAssetField: (id: string): string => id,
  }),
}));

const TS = 1_600_000_000;

function row(
  assetIdentifier: string,
  usdValue: number,
  index: number,
  category: BalanceType = BalanceType.ASSET,
): IndexedBalanceSnapshot {
  return {
    amount: bigNumberify(1),
    assetIdentifier,
    category,
    categoryLabel: category,
    index,
    timestamp: TS,
    usdValue: bigNumberify(usdValue),
  };
}

const rows: IndexedBalanceSnapshot[] = [
  row('ETH', 100, 0),
  row('DAI', 30, 1, BalanceType.LIABILITY),
  row('_nft_0xabc_1', 40, 2),
  row('USDC', 0, 3),
  row('SAITAMA', 5, 4),
];

function identifiersFor(filters: Filters): string[] {
  const { filteredData } = useSnapshotBalanceRows(rows, filters);
  return get(filteredData).map(item => item.assetIdentifier);
}

describe('useSnapshotBalanceRows', () => {
  beforeEach(() => {
    spamIds = ['SAITAMA'];
    ignoredIds = [];
  });

  // Spam, ignored and zero-value rows are hidden unless a pill says otherwise, so an empty bag has
  // to mean what the three ticked checkboxes this replaces meant.
  it('should hide spam, ignored and zero-value rows when no pill is set', () => {
    ignoredIds = ['DAI'];
    expect(identifiersFor({})).toStrictEqual(['ETH', '_nft_0xabc_1']);
  });

  it('should reveal spam rows when the show-spam pill is added', () => {
    expect(identifiersFor({ [SnapshotBalanceFilterKeys.SHOW_SPAM]: true })).toContain('SAITAMA');
  });

  it('should reveal ignored rows when the show-ignored pill is added', () => {
    ignoredIds = ['DAI'];
    expect(identifiersFor({ [SnapshotBalanceFilterKeys.SHOW_IGNORED]: true })).toContain('DAI');
  });

  it('should reveal zero-value rows when the pill asks for all of them', () => {
    expect(identifiersFor({ [SnapshotBalanceFilterKeys.ZERO_VALUE]: ZeroValueFilter.ALL })).toContain('USDC');
  });

  it('should show only the zero-value rows when the pill isolates them', () => {
    expect(identifiersFor({ [SnapshotBalanceFilterKeys.ZERO_VALUE]: ZeroValueFilter.ONLY })).toStrictEqual(['USDC']);
  });

  it('should narrow to one category', () => {
    expect(identifiersFor({ [SnapshotBalanceFilterKeys.CATEGORY]: SnapshotCategories.LIABILITY })).toStrictEqual(['DAI']);
  });

  // An nft is an asset by category, so the two have to be told apart by the identifier.
  it('should tell nfts apart from plain assets', () => {
    expect(identifiersFor({ [SnapshotBalanceFilterKeys.CATEGORY]: SnapshotCategories.NFT })).toStrictEqual(['_nft_0xabc_1']);
    expect(identifiersFor({ [SnapshotBalanceFilterKeys.CATEGORY]: SnapshotCategories.ASSET })).toStrictEqual(['ETH']);
  });

  it('should narrow on written text', () => {
    expect(identifiersFor({ [SnapshotBalanceFilterKeys.SEARCH]: 'eth' })).toStrictEqual(['ETH']);
  });

  // A value the bar cannot have produced, which a hand-written url can.
  it('should ignore a category it does not know', () => {
    expect(identifiersFor({ [SnapshotBalanceFilterKeys.CATEGORY]: 'nonsense' })).toHaveLength(3);
  });

  it('should count the rows the defaults are hiding', () => {
    ignoredIds = ['DAI'];
    const { hiddenCount } = useSnapshotBalanceRows(rows, {});
    // SAITAMA (spam), DAI (ignored) and USDC (zero-value).
    expect(get(hiddenCount)).toBe(3);
  });

  // While isolating, the point is what is shown, not what is hidden, and the pill already says so.
  it('should suppress the hidden count while isolating zero-value rows', () => {
    const { hiddenCount } = useSnapshotBalanceRows(rows, {
      [SnapshotBalanceFilterKeys.ZERO_VALUE]: ZeroValueFilter.ONLY,
    });
    expect(get(hiddenCount)).toBe(0);
  });

  it('should count the zero-value rows the bulk delete would sweep', () => {
    const { zeroValueCount } = useSnapshotBalanceRows(rows, {});
    expect(get(zeroValueCount)).toBe(1);
  });
});
