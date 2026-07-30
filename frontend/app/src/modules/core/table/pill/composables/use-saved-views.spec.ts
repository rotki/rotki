import type { SavedView } from '@/modules/core/table/pill/core/saved-view';
import flushPromises from 'flush-promises';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { type BaseSuggestion, SavedFilterLocation } from '@/modules/core/table/filtering';
import { useSavedViews } from '@/modules/core/table/pill/composables/use-saved-views';
import { useSettingsRepo } from '@/modules/settings/settings-repo';

interface FrontendPatch {
  savedViews?: Partial<Record<SavedFilterLocation, SavedView[]>>;
  savedFilters?: Partial<Record<SavedFilterLocation, BaseSuggestion[][]>>;
}

const updateFrontendSetting = vi.fn(async (_settings: FrontendPatch) => ({ success: true }));

vi.mock('@/modules/settings/use-settings-operations', () => ({
  useSettingsOperations: (): { updateFrontendSetting: typeof updateFrontendSetting } => ({ updateFrontendSetting }),
}));

const location = SavedFilterLocation.HISTORY_EVENTS;

function lastPatch(): FrontendPatch | undefined {
  return updateFrontendSetting.mock.calls.at(-1)?.[0];
}

function storedViews(): SavedView[] {
  return lastPatch()?.savedViews?.[location] ?? [];
}

function view(name: string): SavedView {
  return { matches: {}, name, params: {} };
}

/** Translations are stubbed as `key::args` in unit tests, so a generated name reads as its key. */
function convertedName(number: number): string {
  return `table_filter.saved_views.converted_name::${number}`;
}

describe('useSavedViews', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    updateFrontendSetting.mockClear();
  });

  it('should read back the views of its own location', () => {
    useSettingsRepo().updateFrontend({
      savedViews: { [SavedFilterLocation.ETH_VALIDATORS]: [view('theirs')], [location]: [view('mine')] },
    });

    const { views } = useSavedViews(location);

    expect(get(views).map(entry => entry.name)).toEqual(['mine']);
  });

  it('should store the current state under a name', async () => {
    const { addView } = useSavedViews(location);

    const status = await addView('  Kraken swaps  ', {
      matches: { location: 'kraken' },
      params: { stateMarkers: ['customized'] },
    });

    expect(status.success).toBe(true);
    expect(storedViews()).toEqual([{
      matches: { location: 'kraken' },
      name: 'Kraken swaps',
      params: { stateMarkers: ['customized'] },
    }]);
  });

  it('should reject a name already in use, regardless of case', async () => {
    useSettingsRepo().updateFrontend({ savedViews: { [location]: [view('Kraken')] } });
    const { addView } = useSavedViews(location);

    const status = await addView('kraken', { matches: {}, params: {} });

    expect(status.success).toBe(false);
    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should reject a new view once the location is at its limit', async () => {
    useSettingsRepo().updateFrontend({
      savedViews: { [location]: Array.from({ length: 10 }, (_, i) => view(`view ${i}`)) },
    });
    const { addView } = useSavedViews(location);

    const status = await addView('one more', { matches: {}, params: {} });

    expect(status.success).toBe(false);
    expect(updateFrontendSetting).not.toHaveBeenCalled();
  });

  it('should delete a view by index', async () => {
    useSettingsRepo().updateFrontend({ savedViews: { [location]: [view('a'), view('b'), view('c')] } });
    const { deleteView } = useSavedViews(location);

    await deleteView(1);

    expect(storedViews().map(entry => entry.name)).toEqual(['a', 'c']);
  });

  describe('legacy conversion', () => {
    it('should convert the old saved filters and drop the old key in one write', async () => {
      useSettingsRepo().updateFrontend({
        savedFilters: {
          [SavedFilterLocation.ETH_VALIDATORS]: [[{ key: 'status', value: 'active' }]],
          [location]: [[
            { key: 'location', value: 'kraken' },
            { key: 'type', value: 'trade' },
            { key: 'type', value: 'deposit' },
            { exclude: true, key: 'entryType', value: 'evm event' },
            { key: 'asset', value: { evmChain: null, identifier: 'eip155:1/erc20:0xA0b8', isCustomAsset: false, name: 'USD Coin', symbol: 'USDC' } },
          ]],
        },
      });

      await useSavedViews(location).ensureConverted();

      expect(updateFrontendSetting).toHaveBeenCalledTimes(1);
      expect(storedViews()).toEqual([{
        matches: {
          asset: 'eip155:1/erc20:0xA0b8',
          entryType: '!evm event',
          location: 'kraken',
          type: ['trade', 'deposit'],
        },
        name: convertedName(1),
        params: {},
      }]);
      // Only this location moves: the other two tables still render the old filter bar.
      expect(lastPatch()?.savedFilters).toEqual({
        [SavedFilterLocation.ETH_VALIDATORS]: [[{ key: 'status', value: 'active' }]],
      });
    });

    it('should not write anything when there is nothing to convert', async () => {
      useSettingsRepo().updateFrontend({ savedViews: { [location]: [view('mine')] } });

      await useSavedViews(location).ensureConverted();

      expect(updateFrontendSetting).not.toHaveBeenCalled();
    });

    // Every frontend setting shares one stored blob and a write sends the whole thing, so a
    // conversion firing on mount lands in the burst of writes that logging in produces and is
    // clobbered by a later one built from an older snapshot. Verified in the app before it was
    // moved onto opening the views menu.
    it('should not convert until it is asked to', async () => {
      useSettingsRepo().updateFrontend({
        savedFilters: { [location]: [[{ key: 'location', value: 'kraken' }]] },
      });

      useSavedViews(location);
      await flushPromises();

      expect(updateFrontendSetting).not.toHaveBeenCalled();
    });

    // A legacy filter could hold a date or amount bound, which is stored under its own wire key
    // rather than as a value list; the codec reads those keys straight back as a collapsed pill.
    it('should carry a bound key through unchanged', async () => {
      useSettingsRepo().updateFrontend({
        savedFilters: {
          [location]: [[
            { key: 'fromTimestamp', value: '1785189600' },
            { key: 'maxAmount', value: '100' },
          ]],
        },
      });

      await useSavedViews(location).ensureConverted();

      expect(storedViews()[0].matches).toStrictEqual({ fromTimestamp: '1785189600', maxAmount: '100' });
    });

    // The write clearing the legacy key is what makes this run once, so anything arriving before
    // that write lands has to be held off or the same filters convert twice.
    it('should convert once when asked twice at the same time', async () => {
      useSettingsRepo().updateFrontend({
        savedFilters: { [location]: [[{ key: 'location', value: 'kraken' }]] },
      });
      const { ensureConverted } = useSavedViews(location);

      await Promise.all([ensureConverted(), ensureConverted()]);

      expect(updateFrontendSetting).toHaveBeenCalledTimes(1);
      expect(storedViews()).toHaveLength(1);
    });

    it('should append converted filters after existing views, up to the limit', async () => {
      useSettingsRepo().updateFrontend({
        savedFilters: { [location]: Array.from({ length: 3 }, (_, i) => [{ key: 'location', value: `place ${i}` }]) },
        savedViews: { [location]: Array.from({ length: 9 }, (_, i) => view(`view ${i}`)) },
      });

      await useSavedViews(location).ensureConverted();

      const stored = storedViews();
      expect(stored).toHaveLength(10);
      expect(stored[9]).toEqual({ matches: { location: 'place 0' }, name: convertedName(10), params: {} });
    });
  });
});
