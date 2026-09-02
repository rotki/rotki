import type { LocationLabel } from '@/modules/core/common/location';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useAccountFilterOptions } from '@/modules/history/use-account-filter-options';

const NAMED = '0xAbC1230000000000000000000000000000009876';
const UNNAMED = '0xDeF4560000000000000000000000000000001234';
const NAMED_SHORT = '0xAbC1...9876';
const UNNAMED_SHORT = '0xDeF4...1234';

const names = new Map<string, string>();
const pending = new Set<string>();
const labels = ref<LocationLabel[]>([]);

vi.mock('@/modules/history/use-location-labels', () => ({
  useLocationLabels: vi.fn(() => ({
    getAccountName: (item: LocationLabel): string | undefined => names.get(item.locationLabel),
    getTags: (): string[] => ['tag-one'],
    isAccountNamePending: (item: LocationLabel): boolean => pending.has(item.locationLabel),
    locationLabelOptions: labels,
  })),
}));

vi.mock('@/modules/settings/use-scramble', () => ({
  useScramble: vi.fn(() => ({ scrambleAddress: (address: string): string => address })),
}));

describe('modules/history/use-account-filter-options', () => {
  beforeEach(() => {
    names.clear();
    pending.clear();
    set(labels, []);
  });

  it('should show the name as the label and the address as the caption', () => {
    names.set(NAMED, 'Savings');
    set(labels, [{ location: 'ethereum', locationLabel: NAMED }]);

    const { options } = useAccountFilterOptions();

    expect(get(options)).toEqual([{
      caption: NAMED_SHORT,
      keywords: `${NAMED} savings tag-one`.toLowerCase(),
      label: 'Savings',
      loading: false,
      value: NAMED,
    }]);
  });

  it('should fall back to the address as the label when there is no name', () => {
    set(labels, [{ location: 'ethereum', locationLabel: UNNAMED }]);

    const [option] = get(useAccountFilterOptions().options);

    expect(option.label).toBe(UNNAMED_SHORT);
    expect(option.caption).toBeUndefined();
  });

  it('should mark a row loading only while its name is still resolving', () => {
    pending.add(UNNAMED);
    names.set(NAMED, 'Savings');
    pending.add(NAMED);
    set(labels, [
      { location: 'ethereum', locationLabel: UNNAMED },
      { location: 'ethereum', locationLabel: NAMED },
    ]);

    const [unnamed, named] = get(useAccountFilterOptions().options);

    expect(unnamed.loading).toBe(true);
    // A resolved name wins over a pending lookup: there is nothing left to wait for.
    expect(named.loading).toBe(false);
  });

  it('should emit one option per address across chains', () => {
    set(labels, [
      { location: 'ethereum', locationLabel: UNNAMED },
      { location: 'optimism', locationLabel: UNNAMED },
    ]);

    expect(get(useAccountFilterOptions().options)).toHaveLength(1);
  });

  it('should caption an address only when a name is shown', () => {
    names.set(NAMED, 'Savings');
    set(labels, [
      { location: 'ethereum', locationLabel: NAMED },
      { location: 'ethereum', locationLabel: UNNAMED },
    ]);

    const { resolveCaption, resolveLabel } = useAccountFilterOptions();

    expect(resolveLabel(NAMED)).toBe('Savings');
    expect(resolveCaption(NAMED)).toBe(NAMED_SHORT);
    expect(resolveLabel(UNNAMED)).toBe(UNNAMED_SHORT);
    expect(resolveCaption(UNNAMED)).toBeUndefined();
  });
});
