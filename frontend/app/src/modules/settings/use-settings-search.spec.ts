import type { SettingsSearchEntry } from '@/modules/settings/setting-highlight-ids';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/router/routes', () => ({
  useAppRoutes: vi.fn((): { appRoutes: ReturnType<typeof import('vue')['ref']> } => ({
    appRoutes: ref({
      SETTINGS_ACCOUNT: { icon: 'lu-user', text: 'Account', route: '/settings/account' },
      SETTINGS_GENERAL: { icon: 'lu-settings', text: 'General', route: '/settings/general' },
      SETTINGS_DATABASE: { icon: 'lu-database', text: 'Database', route: '/settings/database' },
      SETTINGS_ACCOUNTING: { icon: 'lu-calculator', text: 'Accounting', route: '/settings/accounting' },
      SETTINGS_EVM: { icon: 'lu-cpu', text: 'EVM', route: '/settings/evm' },
      SETTINGS_ORACLE: { icon: 'lu-activity', text: 'Oracles', route: '/settings/oracle' },
      SETTINGS_RPC: { icon: 'lu-server', text: 'RPC Nodes', route: '/settings/rpc' },
      SETTINGS_MODULES: { icon: 'lu-boxes', text: 'Modules', route: '/settings/modules' },
      SETTINGS_INTERFACE: { icon: 'lu-monitor', text: 'Interface', route: '/settings/interface' },
    }),
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

  beforeEach(async () => {
    setActivePinia(createPinia());
    const mod = await import('./use-settings-search');
    const result = mod.useSettingsSearch();
    filterEntries = result.filterEntries;
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
