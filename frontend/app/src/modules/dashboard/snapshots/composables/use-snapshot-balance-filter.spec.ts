import { describe, expect, it } from 'vitest';
import { ZeroValueFilter } from '@/modules/dashboard/snapshots';
import {
  isolateZeroValue,
  readSnapshotFilters,
  SnapshotBalanceFilterKeys,
  SnapshotCategories,
} from '@/modules/dashboard/snapshots/composables/use-snapshot-balance-filter';

describe('readSnapshotFilters', () => {
  // An empty bag has to mean what the three ticked checkboxes this replaces meant.
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

  // The bag types every value as one-or-many, and the url can carry a repeated key.
  it('should take the first of a repeated value', () => {
    expect(readSnapshotFilters({ [SnapshotBalanceFilterKeys.SEARCH]: ['eth', 'dai'] }).search).toBe('eth');
  });

  // A hand-written url can carry either; neither may reach the predicate as itself.
  it('should fall back on values it does not know', () => {
    const state = readSnapshotFilters({
      [SnapshotBalanceFilterKeys.CATEGORY]: 'nonsense',
      [SnapshotBalanceFilterKeys.ZERO_VALUE]: 'nonsense',
    });

    expect(state.category).toBeUndefined();
    expect(state.zeroValue).toBe(ZeroValueFilter.HIDE);
  });

  // `hide` is the default, so it is not one of the values the pill offers: an absent pill is how
  // the default is stated, and offering it too would give the user two ways to say one thing.
  it('should not treat the default as a settable value', () => {
    expect(readSnapshotFilters({
      [SnapshotBalanceFilterKeys.ZERO_VALUE]: ZeroValueFilter.HIDE,
    }).zeroValue).toBe(ZeroValueFilter.HIDE);
  });

  // Only a real boolean counts; the presence of the key is not enough.
  it('should read a non-boolean show flag as off', () => {
    expect(readSnapshotFilters({ [SnapshotBalanceFilterKeys.SHOW_SPAM]: 'true' }).showSpam).toBe(false);
  });
});

describe('isolateZeroValue', () => {
  // This is what the summary's zero-value warning asks the table for.
  it('should set the zero-value pill to only', () => {
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
