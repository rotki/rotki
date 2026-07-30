import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { FilterValueTypes } from '@/modules/core/table/filtering';
import { useRecentFilterValues } from '@/modules/core/table/pill/composables/use-recent-filter-values';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

interface RecentEntry { count: number; value: string }

interface FrontendPatch { recentFilterValues: Record<string, RecentEntry[]> }

const updateFrontendSetting = vi.fn(async (_settings: FrontendPatch) => ({ success: true }));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): { updateFrontendSetting: typeof updateFrontendSetting } => ({ updateFrontendSetting }),
}));

function field(overrides: Partial<FieldDef> = {}): FieldDef {
  return {
    allowExclusion: false,
    binding: { kind: 'matcher' },
    freeText: true,
    key: 'addresses',
    label: 'Address',
    multiple: true,
    operators: ['is'],
    valueType: FilterValueTypes.ENUM,
    ...overrides,
  };
}

function storedFor(key: string): RecentEntry[] {
  return updateFrontendSetting.mock.calls.at(-1)?.[0].recentFilterValues[key] ?? [];
}

describe('useRecentFilterValues', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    updateFrontendSetting.mockClear();
  });

  it('should remember a committed value', () => {
    const { remember } = useRecentFilterValues();

    remember(field(), ['0xabc']);

    expect(storedFor('addresses')).toEqual([{ count: 1, value: '0xabc' }]);
  });

  it('should not remember values of a field that has its own option list', () => {
    const { remember } = useRecentFilterValues();

    remember(field({ freeText: undefined, key: 'protocols' }), ['aave']);

    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should not remember a value longer than the cap', () => {
    const { remember } = useRecentFilterValues();

    remember(field({ key: 'notesSubstring' }), ['x'.repeat(121)]);

    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should remember a value exactly at the cap', () => {
    const { remember } = useRecentFilterValues();

    remember(field({ key: 'notesSubstring' }), ['x'.repeat(120)]);

    expect(storedFor('notesSubstring')).toHaveLength(1);
  });

  it('should move a re-used value to the front and raise its count', () => {
    const repo = useSettingsRepo();
    repo.updateFrontend({
      recentFilterValues: { addresses: [{ count: 1, value: '0xold' }, { count: 2, value: '0xabc' }] },
    });
    const { remember } = useRecentFilterValues();

    remember(field(), ['0xabc']);

    expect(storedFor('addresses')).toEqual([
      { count: 3, value: '0xabc' },
      { count: 1, value: '0xold' },
    ]);
  });

  it('should keep at most ten values per field', () => {
    const repo = useSettingsRepo();
    repo.updateFrontend({
      recentFilterValues: { addresses: Array.from({ length: 10 }, (_, i) => ({ count: 1, value: `0x${i}` })) },
    });
    const { remember } = useRecentFilterValues();

    remember(field(), ['0xnew']);

    const stored = storedFor('addresses');
    expect(stored).toHaveLength(10);
    expect(stored[0]).toEqual({ count: 1, value: '0xnew' });
    expect(stored.map(entry => entry.value)).not.toContain('0x9');
  });

  it('should read back only the values, most recent first', () => {
    const repo = useSettingsRepo();
    repo.updateFrontend({
      recentFilterValues: { addresses: [{ count: 1, value: '0xa' }, { count: 9, value: '0xb' }] },
    });
    const { recentFor } = useRecentFilterValues();

    expect(recentFor(field())).toEqual(['0xa', '0xb']);
  });
});
