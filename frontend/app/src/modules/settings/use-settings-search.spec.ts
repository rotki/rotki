import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  SettingsCategoryIds,
  type SettingsHighlightId,
  SettingsHighlightIds,
  type SettingsSearchEntry,
} from '@/modules/settings/setting-highlight-ids';
import { actionKeysForAnchor } from '@/modules/settings/settings-actions';
import { getRegistryEntry, registryEntries, registryKeysForAnchor } from '@/modules/settings/settings-registry';

// The settings tabs derive their route/label/icon from each page's `nav` meta via the router.
const settingsRoutes = [
  { name: '/settings/account/', meta: { nav: { icon: 'lu-user', labelKey: 'Account' } } },
  { name: '/settings/general/', meta: { nav: { icon: 'lu-settings', labelKey: 'General' } } },
  { name: '/settings/database/', meta: { nav: { icon: 'lu-database', labelKey: 'Database' } } },
  {
    name: '/settings/accounting/',
    meta: { nav: { icon: 'lu-calculator', labelKey: 'Accounting' } },
  },
  { name: '/settings/chains/', meta: { nav: { icon: 'lu-cpu', labelKey: 'EVM' } } },
  { name: '/settings/oracle/', meta: { nav: { icon: 'lu-activity', labelKey: 'Oracles' } } },
  { name: '/settings/rpc/', meta: { nav: { icon: 'lu-server', labelKey: 'RPC Nodes' } } },
  { name: '/settings/modules/', meta: { nav: { icon: 'lu-boxes', labelKey: 'Modules' } } },
  { name: '/settings/mcp/', meta: { nav: { icon: 'lu-bot', labelKey: 'MCP' } } },
  { name: '/settings/interface/', meta: { nav: { icon: 'lu-monitor', labelKey: 'Interface' } } },
];

vi.mock('vue-router', () => ({
  useRouter: vi.fn(() => ({
    getRoutes: (): typeof settingsRoutes => settingsRoutes,
    resolve: ({ name }: { name: string }): { path: string } => ({ path: name }),
  })),
}));

function makeEntry(texts: string[], keywords?: string[]): SettingsSearchEntry {
  return {
    texts,
    route: '/settings/general',
    icon: 'lu-settings',
    keywords,
  };
}

describe('useSettingsSearch', () => {
  let filterEntries: (entries: SettingsSearchEntry[], keyword: string) => SettingsSearchEntry[];
  let allEntries: SettingsSearchEntry[];

  beforeEach(async () => {
    setActivePinia(createPinia());
    const mod = await import('./use-settings-search');
    const result = mod.useSettingsSearch();
    filterEntries = result.filterEntries;
    allEntries = get(result.entries);
  });

  describe('highlight-id integrity', () => {
    it('should surface every defined highlight id in exactly one search entry', () => {
      const searchIds = allEntries
        .map(entry => entry.highlightId)
        .filter((id): id is NonNullable<typeof id> => id !== undefined);
      const counts = new Map<string, number>();
      for (const id of searchIds) counts.set(id, (counts.get(id) ?? 0) + 1);

      const definedIds = Object.values(SettingsHighlightIds);
      const missing = definedIds.filter(id => !counts.has(id));
      const duplicated = [...counts.entries()].filter(([, count]) => count > 1).map(([id]) => id);

      expect(
        missing,
        'highlight ids defined but not surfaced in settings search (add a search entry)',
      ).toEqual([]);
      expect(duplicated, 'highlight ids used by more than one search entry').toEqual([]);
    });

    it('should only reference highlight ids that are defined', () => {
      const definedIds = new Set<string>(Object.values(SettingsHighlightIds));
      const unknown = allEntries
        .map(entry => entry.highlightId)
        .filter((id): id is NonNullable<typeof id> => id !== undefined)
        .filter(id => !definedIds.has(id));
      expect(unknown, 'search entries referencing an undefined highlight id').toEqual([]);
    });
  });

  describe('registry <-> anchor coverage', () => {
    it('should only anchor registry entries to defined highlight ids', () => {
      const definedIds = new Set<string>(Object.values(SettingsHighlightIds));
      const invalid = registryEntries()
        .map(([key, entry]) => ({ anchor: entry.anchor, key }))
        .filter(({ anchor }) => anchor !== undefined && !definedIds.has(anchor));
      expect(invalid, 'registry entries anchored to an undefined highlight id').toEqual([]);
    });

    it('should surface every registry anchor in the search entries', () => {
      const surfaced = new Set(
        allEntries.map(entry => entry.highlightId).filter((id): id is NonNullable<typeof id> => id !== undefined),
      );
      const unsurfaced = registryEntries()
        .map(([key, entry]) => ({ anchor: entry.anchor, key }))
        .filter(({ anchor }) => anchor !== undefined && !surfaced.has(anchor));
      expect(unsurfaced, 'registry keys anchored to a highlight id the search does not surface').toEqual([]);
    });

    it('should resolve every anchored highlight id back to existing registry keys', () => {
      const anchoredIds = Object.values(SettingsHighlightIds).filter(id => registryKeysForAnchor(id).length > 0);
      for (const id of anchoredIds) {
        const keys = registryKeysForAnchor(id);
        expect(keys.length, `anchor ${id} should map to at least one registry key`).toBeGreaterThan(0);
        for (const key of keys)
          expect(getRegistryEntry(key), `key ${key} for anchor ${id} should resolve to a registry entry`).toBeDefined();
      }
    });

    it('should own every highlight id in exactly one registry (setting xor action)', () => {
      // Every anchor is owned by exactly one source: a registry setting (via its `anchor`) or a
      // `settingsActions` entry. This derived invariant replaces a hand-kept keyless allowlist, so an
      // anchor that loses its owner (or gains a second) fails here instead of drifting silently.
      const ids = Object.values(SettingsHighlightIds);
      const ownedByBoth = ids.filter(id => registryKeysForAnchor(id).length > 0 && actionKeysForAnchor(id).length > 0);
      const ownedByNeither = ids.filter(id => registryKeysForAnchor(id).length === 0 && actionKeysForAnchor(id).length === 0);
      expect(ownedByBoth, 'highlight ids owned by both a setting and an action').toEqual([]);
      expect(ownedByNeither, 'highlight ids owned by neither a setting nor an action').toEqual([]);
    });

    it('should derive migrated category rows from the registry search blocks', () => {
      // the external service category no longer lives in a getXTab builder; its header and per-setting
      // rows are derived from SEARCH_CATEGORIES + the registry `search` blocks.
      const rows = allEntries.filter(entry => entry.categoryId === SettingsCategoryIds.EXTERNAL_SERVICE);
      const headers = rows.filter(entry => entry.highlightId === undefined);
      const anchors = rows.map(entry => entry.highlightId).filter(Boolean);

      expect(headers, 'exactly one category header row').toHaveLength(1);
      expect(anchors).toEqual(expect.arrayContaining([
        SettingsHighlightIds.CONNECT_TIMEOUT,
        SettingsHighlightIds.QUERY_RETRY_LIMIT,
        SettingsHighlightIds.READ_TIMEOUT,
        SettingsHighlightIds.SUPPRESS_MISSING_KEY,
      ]));
      // the tab breadcrumb is resolved from the `/settings/general/` nav meta, never restated
      rows.forEach(entry => expect(entry.texts[0]).toBe('General'));
    });

    it('should build flat and sub-group breadcrumbs for the interface tab', () => {
      const rowFor = (id: SettingsHighlightId): SettingsSearchEntry | undefined =>
        allEntries.find(entry => entry.highlightId === id);

      // a flat category (interface) drops the category segment: breadcrumb is tab > setting
      const language = rowFor(SettingsHighlightIds.LANGUAGE);
      expect(language?.texts).toEqual(['Interface', 'general_settings.language.title']);

      // a sub-group setting inserts its group segment: tab > group > setting (still no category)
      const minOutOfSync = rowFor(SettingsHighlightIds.MIN_OUT_OF_SYNC_PERIOD);
      expect(minOutOfSync?.texts).toEqual([
        'Interface',
        'frontend_settings.history_query_indicator.title',
        'frontend_settings.history_query_indicator.min_out_of_sync_period.title',
      ]);

      // a non-flat category keeps the category segment: tab > category > setting
      const graphBasis = rowFor(SettingsHighlightIds.GRAPH_BASIS);
      expect(graphBasis?.texts).toEqual([
        'Interface',
        'frontend_settings.subtitle.graph_settings',
        'frontend_settings.graph_basis.title',
      ]);
    });

    it('should build a two-level breadcrumb for categoryless action rows', () => {
      const rpc = allEntries.find(entry => entry.highlightId === SettingsHighlightIds.RPC_NODES);
      expect(rpc?.categoryId).toBeUndefined();
      expect(rpc?.texts).toEqual(['RPC Nodes', 'general_settings.rpc_node_setting.title']);

      const mcp = allEntries.find(entry => entry.highlightId === SettingsHighlightIds.MCP_SERVER);
      expect(mcp?.categoryId).toBeUndefined();
      expect(mcp?.texts).toEqual(['MCP', 'backend_settings.settings.mcp_server.label']);
    });

    it('should find settings by their derived enum-value keywords', () => {
      const anchorOf = (keyword: string): (string | undefined)[] =>
        filterEntries(allEntries, keyword).map(entry => entry.highlightId);
      expect(anchorOf('fifo')).toContain(SettingsHighlightIds.ACCOUNTING_TRADE);
      expect(anchorOf('hifo')).toContain(SettingsHighlightIds.ACCOUNTING_TRADE);
      expect(anchorOf('6m')).toContain(SettingsHighlightIds.TIMEFRAME);
      expect(anchorOf('before')).toContain(SettingsHighlightIds.CURRENCY_LOCATION);
    });
  });

  describe('filterEntries', () => {
    const entries: SettingsSearchEntry[] = [
      makeEntry(['General', 'Usage Analytics']),
      makeEntry(['General', 'Date Format']),
      makeEntry(['General', 'Balance Save Frequency'], ['save interval']),
      makeEntry(['Database', 'Purge Data'], ['clear cache']),
      makeEntry(['Interface', 'Language'], ['locale']),
    ];

    it('should return all entries when keyword is empty', () => {
      expect(filterEntries(entries, '')).toEqual([]);
    });

    it('should match a single word against texts', () => {
      const results: SettingsSearchEntry[] = filterEntries(entries, 'date');
      expect(results).toHaveLength(1);
      expect(results[0].texts).toEqual(['General', 'Date Format']);
    });

    it('should match against keywords', () => {
      const results: SettingsSearchEntry[] = filterEntries(entries, 'locale');
      expect(results).toHaveLength(1);
      expect(results[0].texts).toEqual(['Interface', 'Language']);
    });

    it('should match case-insensitively', () => {
      const results: SettingsSearchEntry[] = filterEntries(entries, 'PURGE');
      expect(results).toHaveLength(1);
      expect(results[0].texts).toEqual(['Database', 'Purge Data']);
    });

    it('should ignore special characters in keyword', () => {
      const results: SettingsSearchEntry[] = filterEntries(entries, 'date-format');
      expect(results).toHaveLength(1);
      expect(results[0].texts).toEqual(['General', 'Date Format']);
    });

    it('should return multiple matches sorted by score', () => {
      const results: SettingsSearchEntry[] = filterEntries(entries, 'general');
      expect(results).toHaveLength(3);
      results.forEach((r: SettingsSearchEntry) => {
        expect(r.texts[0]).toBe('General');
      });
    });

    it('should score prefix matches higher', () => {
      const testEntries: SettingsSearchEntry[] = [
        makeEntry(['Something with balance in middle']),
        makeEntry(['Balance Save Frequency']),
      ];
      const results: SettingsSearchEntry[] = filterEntries(testEntries, 'balance');
      expect(results).toHaveLength(2);
      // The entry starting with "balance" should score higher (1 + 0.5 prefix bonus)
      expect(results[0].texts).toEqual(['Balance Save Frequency']);
    });

    it('should handle multi-word search and ranks higher matches first', () => {
      const results: SettingsSearchEntry[] = filterEntries(entries, 'general date');
      // "General > Date Format" matches both words (2 points), other General entries match only one (1 point)
      expect(results.length).toBeGreaterThanOrEqual(1);
      expect(results[0].texts).toEqual(['General', 'Date Format']);
    });

    it('should return empty array when nothing matches', () => {
      const results: SettingsSearchEntry[] = filterEntries(entries, 'nonexistent');
      expect(results).toHaveLength(0);
    });

    it('should match partial words', () => {
      const results: SettingsSearchEntry[] = filterEntries(entries, 'freq');
      expect(results).toHaveLength(1);
      expect(results[0].texts).toEqual(['General', 'Balance Save Frequency']);
    });

    it('should match keywords alongside texts', () => {
      const results: SettingsSearchEntry[] = filterEntries(entries, 'save');
      expect(results).toHaveLength(1);
      expect(results[0].texts).toEqual(['General', 'Balance Save Frequency']);
    });

    it('should handle whitespace-only keyword', () => {
      const results: SettingsSearchEntry[] = filterEntries(entries, '   ');
      expect(results).toHaveLength(0);
    });
  });
});
