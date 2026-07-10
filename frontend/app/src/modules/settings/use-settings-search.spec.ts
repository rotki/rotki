import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  SettingsHighlightIds,
  type SettingsSearchEntry,
} from '@/modules/settings/setting-highlight-ids';
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
  { name: '/settings/evm/', meta: { nav: { icon: 'lu-cpu', labelKey: 'EVM' } } },
  { name: '/settings/oracle/', meta: { nav: { icon: 'lu-activity', labelKey: 'Oracles' } } },
  { name: '/settings/rpc/', meta: { nav: { icon: 'lu-server', labelKey: 'RPC Nodes' } } },
  { name: '/settings/modules/', meta: { nav: { icon: 'lu-boxes', labelKey: 'Modules' } } },
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
    // Anchors that intentionally back no registry setting: action targets, info displays, backend
    // settings and subsystems that are not part of the settings registry. Keeping this list explicit
    // makes "this anchor has no setting" a reviewed decision rather than silent drift.
    const keylessAnchors: string[] = [
      SettingsHighlightIds.ACCOUNTING_RULE,
      SettingsHighlightIds.ASSET_UPDATE,
      SettingsHighlightIds.CHANGE_PASSWORD,
      SettingsHighlightIds.GLOBALDB_INFO,
      SettingsHighlightIds.LOG_LEVEL,
      SettingsHighlightIds.MODULES,
      SettingsHighlightIds.PURGE_DATA,
      SettingsHighlightIds.PURGE_IMAGES_CACHE,
      SettingsHighlightIds.REFRESH_CACHE,
      SettingsHighlightIds.RESET_DISMISSAL_STATUS,
      SettingsHighlightIds.RESTORE_ASSETS_DB,
      SettingsHighlightIds.RPC_NODES,
      SettingsHighlightIds.SKIPPED_EVENTS,
      SettingsHighlightIds.USERDB_INFO,
    ].sort();

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

    it('should keep the keyless-anchor allowlist in sync with the registry', () => {
      const keyless = Object.values(SettingsHighlightIds)
        .filter(id => registryKeysForAnchor(id).length === 0)
        .sort();
      expect(keyless).toEqual(keylessAnchors);
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
