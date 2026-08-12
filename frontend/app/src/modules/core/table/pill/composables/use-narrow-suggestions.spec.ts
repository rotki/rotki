import type { AssetsWithId } from '@/modules/assets/types';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { ref } from 'vue';
import { FilterValueTypes } from '@/modules/core/table/filtering';
import { useNarrowSuggestions } from '@/modules/core/table/pill/composables/use-narrow-suggestions';

function field(overrides: Partial<FieldDef> & Pick<FieldDef, 'key' | 'label'>): FieldDef {
  return {
    allowExclusion: false,
    binding: { kind: 'filter' },
    multiple: true,
    operators: ['is'],
    valueType: FilterValueTypes.ENUM,
    ...overrides,
  };
}

const protocol = field({
  key: 'protocol',
  label: 'Protocol',
  suggest: (): string[] => ['aave'],
});

function assetField(searchAsset: (value: string) => Promise<AssetsWithId>): FieldDef {
  return field({ key: 'asset', label: 'Asset', searchAsset, valueType: FilterValueTypes.ASSET });
}

function asset(identifier: string, symbol: string, evmChain?: string): AssetsWithId[number] {
  return { assetType: 'evm token', evmChain, identifier, isCustomAsset: false, name: `${symbol} coin`, symbol };
}

describe('useNarrowSuggestions', () => {
  beforeEach(() => {
    // The composable reads the remembered free-text values out of the settings repo.
    setActivePinia(createPinia());
    vi.useFakeTimers();
  });

  it('should offer every field before anything is typed', () => {
    const { suggestions } = useNarrowSuggestions(ref(''), ref([protocol]));

    expect(get(suggestions)).toEqual([{ field: protocol, kind: 'field', label: 'Protocol' }]);
  });

  it('should append asset matches after the synchronous ones', async () => {
    const search = vi.fn(async (): Promise<AssetsWithId> => [asset('eip155:1/erc20:0xa0b', 'USDC', 'ethereum')]);
    const fields = [protocol, assetField(search)];
    const query = ref('usdc');
    const { suggestions } = useNarrowSuggestions(query, ref(fields));

    // Before the debounce elapses only the pure matches are there.
    expect(get(suggestions)).toEqual([]);

    await vi.advanceTimersByTimeAsync(400);

    expect(get(suggestions)).toEqual([
      {
        caption: 'USDC coin',
        chain: 'ethereum',
        field: fields[1],
        kind: 'value',
        label: 'USDC',
        value: 'eip155:1/erc20:0xa0b',
      },
    ]);
    expect(search).toHaveBeenCalledWith('usdc');
  });

  it('should not search until the query settles', async () => {
    const search = vi.fn(async (): Promise<AssetsWithId> => []);
    const query = ref('u');
    useNarrowSuggestions(query, ref([assetField(search)]));

    set(query, 'us');
    set(query, 'usd');
    await vi.advanceTimersByTimeAsync(400);

    expect(search).toHaveBeenCalledTimes(1);
    expect(search).toHaveBeenCalledWith('usd');
  });

  it('should ignore a slow response that a newer search has replaced', async () => {
    const search = vi.fn()
      .mockImplementationOnce(async (): Promise<AssetsWithId> => new Promise((resolve) => {
        setTimeout(() => resolve([asset('stale', 'STALE')]), 500);
      }))
      .mockImplementationOnce(async (): Promise<AssetsWithId> => [asset('fresh', 'FRESH')]);
    const fields = [assetField(search)];
    const query = ref('sta');
    const { suggestions } = useNarrowSuggestions(query, ref(fields));

    await vi.advanceTimersByTimeAsync(400);
    set(query, 'fres');
    await vi.advanceTimersByTimeAsync(400);
    // The first search resolves only now, long after the second already published.
    await vi.advanceTimersByTimeAsync(500);

    expect(get(suggestions).map(entry => entry.label)).toEqual(['FRESH']);
  });

  it('should keep the rest of the list when the search fails', async () => {
    const search = vi.fn(async (): Promise<AssetsWithId> => {
      throw new Error('offline');
    });
    const fields = [protocol, assetField(search)];
    const { loading, suggestions } = useNarrowSuggestions(ref('aave'), ref(fields));

    await vi.advanceTimersByTimeAsync(400);

    expect(get(suggestions)).toEqual([{ field: protocol, kind: 'value', label: 'aave', value: 'aave' }]);
    expect(get(loading)).toBe(false);
  });

  it('should report while a search is in flight', async () => {
    const search = vi.fn(async (): Promise<AssetsWithId> => new Promise((resolve) => {
      setTimeout(resolve, 200, []);
    }));
    const { loading } = useNarrowSuggestions(ref('usdc'), ref([assetField(search)]));

    await vi.advanceTimersByTimeAsync(400);
    expect(get(loading)).toBe(true);

    await vi.advanceTimersByTimeAsync(200);
    expect(get(loading)).toBe(false);
  });
});
