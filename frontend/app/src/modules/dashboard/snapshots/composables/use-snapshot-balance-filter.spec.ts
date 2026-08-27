import { describe, expect, it } from 'vitest';
import { ZeroValueFilter } from '@/modules/dashboard/snapshots';
import {
  isolateZeroValue,
  readSnapshotFilters,
  SnapshotBalanceFilterKeys,
  SnapshotCategories,
} from '@/modules/dashboard/snapshots/composables/use-snapshot-balance-filter';

describe('readSnapshotFilters', () => {
  it('should read an empty bag as the table defaults', () => {
    expect(readSnapshotFilters({})).toStrictEqual({
      category: undefined,
      search: '',
      showIgnored: false,
      showSpam: false,
      zeroValue: ZeroValueFilter.HIDE,
    });
  });

  it('should read the three departures a pill can state', () => {
    const state = readSnapshotFilters({
      [SnapshotBalanceFilterKeys.SHOW_IGNORED]: true,
      [SnapshotBalanceFilterKeys.SHOW_SPAM]: true,
      [SnapshotBalanceFilterKeys.ZERO_VALUE]: ZeroValueFilter.ONLY,
    });

    expect(state.showIgnored).toBe(true);
    expect(state.showSpam).toBe(true);
    expect(state.zeroValue).toBe(ZeroValueFilter.ONLY);
  });

  it('should read the category and the written text', () => {
    const state = readSnapshotFilters({
      [SnapshotBalanceFilterKeys.CATEGORY]: SnapshotCategories.LIABILITY,
      [SnapshotBalanceFilterKeys.SEARCH]: 'eth',
    });

    expect(state.category).toBe(SnapshotCategories.LIABILITY);
    expect(state.search).toBe('eth');
  });

  it('should take the first of a repeated value, which the url can carry', () => {
    expect(readSnapshotFilters({ [SnapshotBalanceFilterKeys.SEARCH]: ['eth', 'dai'] }).search).toBe('eth');
  });

  it('should fall back on values it does not know, rather than let one reach the predicate', () => {
    const state = readSnapshotFilters({
      [SnapshotBalanceFilterKeys.CATEGORY]: 'nonsense',
      [SnapshotBalanceFilterKeys.ZERO_VALUE]: 'nonsense',
    });

    expect(state.category).toBeUndefined();
    expect(state.zeroValue).toBe(ZeroValueFilter.HIDE);
  });

  it('should not treat the default as a settable value', () => {
    expect(readSnapshotFilters({
      [SnapshotBalanceFilterKeys.ZERO_VALUE]: ZeroValueFilter.HIDE,
    }).zeroValue).toBe(ZeroValueFilter.HIDE);
  });

  it('should read a non-boolean show flag as off, the presence of the key not being enough', () => {
    expect(readSnapshotFilters({ [SnapshotBalanceFilterKeys.SHOW_SPAM]: 'true' }).showSpam).toBe(false);
  });
});

describe('isolateZeroValue', () => {
  it('should set the zero-value pill to only, which is what the summary warning asks for', () => {
    expect(isolateZeroValue({})).toStrictEqual({
      [SnapshotBalanceFilterKeys.ZERO_VALUE]: ZeroValueFilter.ONLY,
    });
  });

  it('should leave the other pills alone', () => {
    const isolated = isolateZeroValue({ [SnapshotBalanceFilterKeys.SEARCH]: 'eth' });

    expect(isolated[SnapshotBalanceFilterKeys.SEARCH]).toBe('eth');
    expect(isolated[SnapshotBalanceFilterKeys.ZERO_VALUE]).toBe(ZeroValueFilter.ONLY);
  });
});
