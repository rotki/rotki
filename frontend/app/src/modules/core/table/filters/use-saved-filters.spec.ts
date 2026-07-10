import { assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type BaseSuggestion, SavedFilterLocation, type Suggestion } from '@/modules/core/table/filtering';
import { useSavedFilter } from '@/modules/core/table/filters/use-saved-filters';

type SavedFilters = Partial<Record<SavedFilterLocation, BaseSuggestion[][]>>;

const mockSavedFilters = ref<SavedFilters>({});
const mockUpdateFrontendSetting = vi.fn(async (_setting: { savedFilters: SavedFilters }) => ({ success: true }));

vi.mock('@/modules/settings/use-setting', () => ({
  useSetting: vi.fn(() => mockSavedFilters),
}));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): { updateFrontendSetting: typeof mockUpdateFrontendSetting } => ({
    updateFrontendSetting: mockUpdateFrontendSetting,
  }),
}));

vi.mock('vue-i18n', async importOriginal => ({
  ...await importOriginal<typeof import('vue-i18n')>(),
  useI18n: (): { t: (key: string, args?: Record<string, unknown>) => string } => ({
    t: (key: string, args?: Record<string, unknown>): string => (args ? `${key}::${JSON.stringify(args)}` : key),
  }),
}));

const LOCATION = SavedFilterLocation.HISTORY_EVENTS;

function suggestion(overrides: Partial<Suggestion> = {}): Suggestion {
  return { asset: false, index: 0, key: 'type', total: 1, value: 'deposit', ...overrides };
}

describe('useSavedFilter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    set(mockSavedFilters, {});
    mockUpdateFrontendSetting.mockResolvedValue({ success: true });
  });

  it('should expose an empty list when no filters are saved for the location', () => {
    const { savedFilters } = useSavedFilter(LOCATION, () => false);
    expect(get(savedFilters)).toEqual([]);
  });

  it('should decorate saved base suggestions with asset, index and total', () => {
    set(mockSavedFilters, { [LOCATION]: [[{ key: 'asset', value: 'ETH' }]] });
    const isAsset = (key: string): boolean => key === 'asset';
    const { savedFilters } = useSavedFilter(LOCATION, isAsset);
    expect(get(savedFilters)).toEqual([[{ asset: true, index: 0, key: 'asset', total: 1, value: 'ETH' }]]);
  });

  it('should persist filters for the location via the frontend setting', async () => {
    const { saveFilters } = useSavedFilter(LOCATION, () => false);
    await saveFilters([[{ key: 'type', value: 'deposit' }]]);
    expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({
      savedFilters: { [LOCATION]: [[{ key: 'type', value: 'deposit' }]] },
    });
  });

  it('should append a new filter when under the limit', async () => {
    const { addFilter } = useSavedFilter(LOCATION, () => false);
    const status = await addFilter([suggestion()]);
    expect(status).toEqual({ success: true });
    expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({
      savedFilters: { [LOCATION]: [[{ exclude: undefined, key: 'type', value: 'deposit' }]] },
    });
  });

  it('should use the asset identifier when saving an asset suggestion', async () => {
    const { addFilter } = useSavedFilter(LOCATION, () => true);
    await addFilter([suggestion({ asset: true, key: 'asset', value: { identifier: 'ETH' } })]);
    expect(mockUpdateFrontendSetting).toHaveBeenCalledWith({
      savedFilters: { [LOCATION]: [[{ exclude: undefined, key: 'asset', value: 'ETH' }]] },
    });
  });

  it('should reject adding a filter when the location limit is reached', async () => {
    const existing = Array.from({ length: 10 }, () => [{ key: 'type', value: 'deposit' }]);
    set(mockSavedFilters, { [LOCATION]: existing });
    const { addFilter } = useSavedFilter(LOCATION, () => false);

    const status = await addFilter([suggestion()]);

    expect(status.success).toBe(false);
    expect(mockUpdateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should delete a saved filter by index', async () => {
    set(mockSavedFilters, { [LOCATION]: [[{ key: 'a', value: '1' }], [{ key: 'b', value: '2' }]] });
    const { deleteFilter } = useSavedFilter(LOCATION, () => false);

    await deleteFilter(0);

    const saved = mockUpdateFrontendSetting.mock.calls[0][0].savedFilters[LOCATION];
    assert(saved);
    expect(saved).toHaveLength(1);
    expect(saved[0][0].key).toBe('b');
  });
});
