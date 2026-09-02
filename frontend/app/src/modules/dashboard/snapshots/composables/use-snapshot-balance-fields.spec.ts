import { describe, expect, it } from 'vitest';
import { resolveText } from '@/modules/core/table/pill/core/text';
import { ZeroValueFilter } from '@/modules/dashboard/snapshots';
import { useSnapshotBalanceFields } from '@/modules/dashboard/snapshots/composables/use-snapshot-balance-fields';
import { SnapshotBalanceFilterKeys } from '@/modules/dashboard/snapshots/composables/use-snapshot-balance-filter';

const counts = { ignored: 2, spam: 3, zeroValue: 4 };

describe('useSnapshotBalanceFields', () => {
  it('should offer every filter the header used to carry', () => {
    expect(get(useSnapshotBalanceFields(counts)).map(field => field.key)).toStrictEqual([
      SnapshotBalanceFilterKeys.SEARCH,
      SnapshotBalanceFilterKeys.CATEGORY,
      SnapshotBalanceFilterKeys.SHOW_SPAM,
      SnapshotBalanceFilterKeys.SHOW_IGNORED,
      SnapshotBalanceFilterKeys.ZERO_VALUE,
    ]);
  });

  it('should state the spam and ignored pills as showing, not hiding', () => {
    const [, , spam, ignored] = get(useSnapshotBalanceFields(counts));

    expect(resolveText(spam.label)).toContain('show_spam');
    expect(resolveText(ignored.label)).toContain('show_ignored');
  });

  it('should carry no value, only presence, for the two show flags', () => {
    const [, , spam, ignored] = get(useSnapshotBalanceFields(counts));

    expect(spam.valueType).toBe('boolean');
    expect(ignored.valueType).toBe('boolean');
    expect(spam.suggest).toBeUndefined();
  });

  it('should offer only the two zero-value departures, the default being absence', () => {
    const [, , , , zeroValue] = get(useSnapshotBalanceFields(counts));

    expect(zeroValue.suggest?.()).toStrictEqual([ZeroValueFilter.ALL, ZeroValueFilter.ONLY]);
    expect(zeroValue.suggest?.()).not.toContain(ZeroValueFilter.HIDE);
  });

  it('should read each zero-value choice as words rather than the wire token', () => {
    const [, , , , zeroValue] = get(useSnapshotBalanceFields(counts));

    expect(zeroValue.resolveLabel?.(ZeroValueFilter.ALL)).toContain('zero_value.shown');
    expect(zeroValue.resolveLabel?.(ZeroValueFilter.ONLY)).toContain('zero_value.only');
  });

  it('should rebuild the labels when the counts change, a choice reading differently at zero', () => {
    const model = ref({ ignored: 0, spam: 0, zeroValue: 0 });
    const fields = useSnapshotBalanceFields(model);
    const labelOf = (): string => resolveText(get(fields)[2].label);

    const before = labelOf();
    set(model, { ignored: 0, spam: 7, zeroValue: 0 });

    expect(labelOf()).not.toBe(before);
  });

  it('should name each category rather than showing the wire value', () => {
    const [, category] = get(useSnapshotBalanceFields(counts));

    expect(category.suggest?.()).toStrictEqual(['asset', 'liability', 'nft']);
    expect(category.resolveLabel?.('liability')).toContain('balances.liability');
  });

  it('should type the search rather than pick it', () => {
    const [search] = get(useSnapshotBalanceFields(counts));

    expect(search.freeText).toBe(true);
  });
});
