import type { HistoryEventEntryType } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';

/**
 * Persists the verbs a user picks per entry type so the picker can pin the ones they reach for
 * most to the top. Ranking is frequency-first with recency as the tiebreaker, so a long-favoured
 * verb keeps its spot while ties resolve to whatever was touched last.
 *
 * Storage is a versioned envelope: bumping `RECENT_SCHEMA_VERSION` discards older shapes instead
 * of trying to migrate them.
 */

const RECENT_SCHEMA_VERSION = 2;
const RECENT_LIMIT = 5;
const RECENT_TRACK_LIMIT = 20;
const RECENT_STORAGE_KEY = 'rotki.history.recent-actions';
const RECENT_SCOPE_FALLBACK = '__all__';

interface RecentEntry {
  verbKey: string;
  count: number;
}

interface RecentActionsStore {
  schemaVersion: number;
  /** Picked verbs per scope, most-recent first, so array position is the tiebreaker for equal counts. */
  entries: Record<string, RecentEntry[]>;
}

interface UseRecentActionsReturn {
  readonly recent: ComputedRef<readonly string[]>;
  readonly record: (verbKey: string) => void;
}

function defaultStore(): RecentActionsStore {
  return { entries: {}, schemaVersion: RECENT_SCHEMA_VERSION };
}

export function useRecentActions(
  entryType?: MaybeRefOrGetter<HistoryEventEntryType | undefined>,
): UseRecentActionsReturn {
  const store = useLocalStorage<RecentActionsStore>(RECENT_STORAGE_KEY, defaultStore());

  /**
   * Reads the persisted store, substituting an empty one when the key has been cleared.
   *
   * @remarks
   * `useLocalStorage` returns a `RemovableRef`, so its value can be `null` at any point and every
   * read goes through here rather than touching the ref directly.
   */
  function currentStore(): RecentActionsStore {
    return get(store) ?? defaultStore();
  }

  // Discard incompatible persisted shapes rather than risk reading stale data.
  if (currentStore().schemaVersion !== RECENT_SCHEMA_VERSION)
    set(store, defaultStore());

  const scopeKey = computed<string>(() => toValue(entryType) ?? RECENT_SCOPE_FALLBACK);

  // A stable sort by count over a recency-ordered array leaves the newest verb first on ties.
  const recent = computed<readonly string[]>(() => {
    const entries = currentStore().entries[get(scopeKey)] ?? [];
    return entries
      .slice()
      .sort((a, b) => b.count - a.count)
      .slice(0, RECENT_LIMIT)
      .map(entry => entry.verbKey);
  });

  function record(verbKey: string): void {
    const key = get(scopeKey);
    const current = currentStore();
    const existing = current.entries[key] ?? [];
    const previous = existing.find(entry => entry.verbKey === verbKey);

    // Move the picked verb to the front (recency) and bump its count (frequency).
    const next: RecentEntry[] = [
      { count: (previous?.count ?? 0) + 1, verbKey },
      ...existing.filter(entry => entry.verbKey !== verbKey),
    ].slice(0, RECENT_TRACK_LIMIT);

    set(store, {
      ...current,
      entries: {
        ...current.entries,
        [key]: next,
      },
    });
  }

  return {
    recent,
    record,
  };
}
