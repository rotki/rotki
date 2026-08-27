import type { RouteActionEntry, RouteSearchEntry } from '@/modules/shell/layout/use-route-search';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useGlobalSearch } from '@/modules/shell/layout/use-global-search';

const searchEntries = ref<RouteSearchEntry[]>([]);
const actionEntries = ref<RouteActionEntry[]>([]);

vi.mock('pinia', async importOriginal => ({
  ...(await importOriginal<object>()),
  storeToRefs: (store: unknown): unknown => store,
}));
vi.mock('@/modules/shell/layout/use-route-search', () => ({
  useRouteSearch: (): { searchEntries: typeof searchEntries; actionEntries: typeof actionEntries } => ({ searchEntries, actionEntries }),
}));
vi.mock('@/modules/balances/exchanges/use-connected-exchanges-store', () => ({
  useConnectedExchangesStore: (): { connectedExchanges: Ref<unknown[]> } => ({ connectedExchanges: ref([]) }),
}));
vi.mock('@/modules/balances/use-aggregated-balances', () => ({
  useAggregatedBalances: (): Record<string, unknown> => ({
    balancesByChainLocation: ref({}),
    balancesByLocation: ref({}),
    getBalances: (): unknown[] => [],
  }),
}));
vi.mock('@/modules/core/common/use-locations', () => ({
  useLocations: (): { getLocationData: () => undefined } => ({ getLocationData: (): undefined => undefined }),
}));
vi.mock('@/modules/assets/use-asset-info-retrieval', () => ({
  useAssetInfoRetrieval: (): { assetSearch: () => Promise<unknown[]> } => ({ assetSearch: async (): Promise<unknown[]> => [] }),
}));

function entry(path: string, labelKey: string, parentLabelKey?: string): RouteSearchEntry {
  return { path, labelKey, parentLabelKey, icon: 'lu-list', keywordKeys: [] };
}

describe('modules::shell::use-global-search', () => {
  beforeEach(() => {
    set(searchEntries, []);
    set(actionEntries, []);
  });

  it('should return nothing for an empty keyword', async () => {
    const { search } = useGlobalSearch();
    expect(await search('')).toStrictEqual([]);
  });

  it('should match navigable routes by label and assign sequential values', async () => {
    set(searchEntries, [entry('/dashboard/', 'dashboard overview'), entry('/nfts/', 'gallery')]);

    const { search } = useGlobalSearch();
    const results = await search('dashboard');

    expect(results).toHaveLength(1);
    expect(results[0].route).toBe('/dashboard/');
    expect(results[0].value).toBe(0);
  });

  it('should surface quick add actions with the add icon', async () => {
    set(actionEntries, [{ path: '/tag-manager/?add=true', labelKey: 'create tag' }]);

    const { search } = useGlobalSearch();
    const results = await search('create');

    expect(results).toHaveLength(1);
    expect(results[0].icon).toBe('lu-circle-plus');
    expect(results[0].route).toBe('/tag-manager/?add=true');
  });

  it('should exclude entries that do not match the keyword', async () => {
    set(searchEntries, [entry('/dashboard/', 'dashboard'), entry('/nfts/', 'gallery')]);

    const { search } = useGlobalSearch();
    const results = await search('gallery');

    expect(results.map(item => item.route)).toStrictEqual(['/nfts/']);
  });
});
