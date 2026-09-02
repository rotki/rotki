import type { RuiIcons } from '@rotki/ui-library';
import type { Ref } from 'vue';
import type { MessageKey } from '@/message-key';
import type { RouteName } from '@/types/router';
import { getTextToken, TimeFramePeriod } from '@rotki/common';
import { groupBy } from 'es-toolkit';
import { CurrencyLocation } from '@/modules/assets/amount-display/currency-location';
import { type SettingsCategoryId, type SettingsHighlightId, SettingsHighlightIds, type SettingsSearchEntry } from '@/modules/settings/setting-highlight-ids';
import { actionEntries } from '@/modules/settings/settings-actions';
import { registryEntries } from '@/modules/settings/settings-registry';
import { SEARCH_CATEGORIES, type SearchCategory } from '@/modules/settings/settings-search-catalog';
import { CostBasisMethod } from '@/modules/settings/types/user-settings';

/**
 * Extra search keywords derived from a setting's option domain, so a value like `fifo` or `6m` finds
 * its setting even though the value is never rendered as UI text. Only anchors whose option set is a
 * cleanly-importable enum qualify (see the fold plan); everything else keeps its hand-written keywords.
 */
const anchorKeywordDomains: Partial<Record<SettingsHighlightId, readonly string[]>> = {
  [SettingsHighlightIds.ACCOUNTING_TRADE]: Object.values(CostBasisMethod),
  [SettingsHighlightIds.CURRENCY_LOCATION]: Object.values(CurrencyLocation),
  [SettingsHighlightIds.TIMEFRAME]: Object.values(TimeFramePeriod),
};

interface TabInfo {
  icon: RuiIcons;
  text: string;
  route: string;
}

type T = ReturnType<typeof useI18n>['t'];

interface UseSettingsSearchReturn {
  entries: Readonly<Ref<SettingsSearchEntry[]>>;
  filterEntries: (entries: SettingsSearchEntry[], keyword: string) => SettingsSearchEntry[];
}

interface DerivedRow {
  readonly category?: SettingsCategoryId;
  readonly tab?: RouteName;
  readonly group?: MessageKey;
  readonly titleKey: MessageKey;
  readonly keywords?: readonly MessageKey[];
  readonly highlightId?: SettingsHighlightId;
}

/** Translates the hand-written keywords and merges in any anchor-derived enum-value keywords. */
function mergeKeywords(t: T, highlightId: SettingsHighlightId | undefined, keywords: readonly MessageKey[] | undefined): string[] | undefined {
  const derived = highlightId ? anchorKeywordDomains[highlightId] : undefined;
  const base = keywords?.map(key => t(key));
  if (!derived)
    return base;
  return [...new Set([...(base ?? []), ...derived])];
}

/**
 * Every search row flattened from its two sources: a registry entry's `search` block (its highlight id
 * is the entry `anchor`) and the `settingsActions` registry (action/info/keyless rows, keyed by action).
 * A row either nests under a `category` header or sits directly on a `tab`.
 */
function collectRows(): DerivedRow[] {
  const rows: DerivedRow[] = [];
  for (const [, entry] of registryEntries()) {
    const { anchor, search } = entry;
    if (search)
      rows.push({ category: search.category, group: search.group, highlightId: anchor, keywords: search.keywords, tab: search.tab, titleKey: search.titleKey });
  }
  for (const [, action] of actionEntries()) {
    rows.push({ category: action.category, group: action.group, highlightId: action.anchor, keywords: action.keywords, tab: action.tab, titleKey: action.titleKey });
  }
  return rows;
}

/** A row's optional group heading, as the zero or one text segment it contributes. */
function rowGroup(row: DerivedRow, t: T): string[] {
  return row.group ? [t(row.group)] : [];
}

/**
 * Derives every search row from the registry and the catalog.
 *
 * @remarks
 * Each `SEARCH_CATEGORIES` entry emits a header row plus its member rows, and a categoryless row
 * sits directly on its tab. A row's breadcrumb is `tab > [category unless flat] > [group] > title`.
 */
function derivedSearchEntries(tabInfo: (name: RouteName) => TabInfo | undefined, t: T): SettingsSearchEntry[] {
  const rows = collectRows();
  const placed = rows.filter((row): row is DerivedRow & { category: SettingsCategoryId } => row.category !== undefined);
  const byCategory = groupBy(placed, row => row.category);
  const looseRows = rows.filter(row => row.category === undefined);

  const toEntry = (info: TabInfo, row: DerivedRow, texts: string[]): SettingsSearchEntry => ({
    categoryId: row.category,
    highlightId: row.highlightId,
    icon: info.icon,
    keywords: mergeKeywords(t, row.highlightId, row.keywords),
    route: info.route,
    texts,
  });

  /**
   * Builds the searchable entries for one category, led by an entry for the header itself.
   *
   * @remarks
   * A flat category has no header text, so its rows carry no category prefix in their match text.
   */
  const categoryEntries = (category: SearchCategory, info: TabInfo): SettingsSearchEntry[] => {
    const categoryTitle = t(category.titleKey);
    const header: SettingsSearchEntry = {
      categoryId: category.id,
      icon: info.icon,
      keywords: category.keywords?.map(key => t(key)),
      route: info.route,
      texts: [info.text, categoryTitle],
    };

    const prefix = category.flat ? [] : [categoryTitle];
    const rows = (byCategory[category.id] ?? []).map(row =>
      toEntry(info, row, [info.text, ...prefix, ...rowGroup(row, t), t(row.titleKey)]),
    );

    return [header, ...rows];
  };

  const entries: SettingsSearchEntry[] = [];

  for (const category of SEARCH_CATEGORIES) {
    const info = tabInfo(category.tab);
    if (info)
      entries.push(...categoryEntries(category, info));
  }

  // Rows that name a tab but sit under no category heading.
  for (const row of looseRows) {
    const info = row.tab ? tabInfo(row.tab) : undefined;
    if (info)
      entries.push(toEntry(info, row, [info.text, ...rowGroup(row, t), t(row.titleKey)]));
  }

  return entries;
}

/**
 * The normalized text a row is matched against, cached per entry object. Entries are rebuilt only when
 * the search `computed` re-runs (locale/route change), so tokens are recomputed at that cadence rather
 * than re-tokenizing every row on each keystroke.
 */
const searchTokens = new WeakMap<SettingsSearchEntry, string>();

function getSearchToken(entry: SettingsSearchEntry): string {
  const cached = searchTokens.get(entry);
  if (cached !== undefined)
    return cached;
  const token = getTextToken([...entry.texts, ...(entry.keywords ?? [])].join(' '));
  searchTokens.set(entry, token);
  return token;
}

export function useSettingsSearch(): UseSettingsSearchReturn {
  const { t } = useI18n({ useScope: 'global' });
  const router = useRouter();

  /**
   * Resolves a settings tab's route, label and icon from that page's `nav` meta.
   *
   * @returns `undefined` when the route declares no `nav`, which drops that one tab from the
   * search rather than failing the whole derivation
   */
  function tabInfo(name: RouteName): TabInfo | undefined {
    const nav = router.getRoutes().find(route => route.name === name)?.meta.nav;
    if (!nav)
      return undefined;
    return {
      icon: nav.icon,
      route: router.resolve({ name }).path,
      text: t(nav.labelKey),
    };
  }

  const entries = computed<SettingsSearchEntry[]>(() => derivedSearchEntries(tabInfo, t));

  function filterEntries(entries: SettingsSearchEntry[], keyword: string): SettingsSearchEntry[] {
    const words: string[] = keyword.split(/\s+/).map((w: string) => getTextToken(w)).filter(Boolean);
    const scored: { entry: SettingsSearchEntry; points: number }[] = entries.map((e: SettingsSearchEntry) => {
      let points: number = 0;
      const text: string = getSearchToken(e);
      for (const word of words) {
        const idx: number = text.indexOf(word);
        if (idx > -1) {
          points++;
          if (idx === 0)
            points += 0.5;
        }
      }
      return { entry: e, points };
    });
    return scored
      .filter(s => s.points > 0)
      .sort((a, b) => b.points - a.points)
      .map(s => s.entry);
  }

  return {
    entries,
    filterEntries,
  };
}
