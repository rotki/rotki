import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { ActionStatus } from '@/modules/core/common/action';
import type { BaseSuggestion, SavedFilterLocation } from '@/modules/core/table/filtering';
import type { SavedView } from '@/modules/core/table/pill/core/saved-view';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

/** Kept from the filter bar this replaces: enough for the handful of views a user curates. */
const LIMIT_PER_LOCATION = 10;

/**
 * A view without its name: the bar's two models. The codec's `SerializedState` is one of these,
 * which is what makes saving a matter of handing over what the bar already produced.
 */
export type SavedViewState = Pick<SavedView, 'matches' | 'params'>;

interface SavedViewsReturn {
  views: ComputedRef<SavedView[]>;
  /** Stores the bar's current state under a name. Fails on a blank or duplicate name, or at the cap. */
  addView: (name: string, state: SavedViewState) => Promise<ActionStatus>;
  deleteView: (index: number) => Promise<ActionStatus>;
  /** Migrates this location's legacy saved filters, once. Call it when the views UI is opened. */
  ensureConverted: () => Promise<void>;
}

/**
 * Folds one legacy saved filter into a view's `matches`. The old shape is a flat list of one
 * suggestion per value, so several entries can share a key: they become that key's value list,
 * which is the form the codec reads.
 */
function matchesFromSuggestions(suggestions: BaseSuggestion[]): SavedView['matches'] {
  const grouped = new Map<string, (string | boolean)[]>();

  for (const suggestion of suggestions) {
    const raw = suggestion.value;
    // An asset suggestion stored its whole info object; the identifier is what goes on the wire.
    const value = typeof raw === 'string' || typeof raw === 'boolean' ? raw : raw.identifier;
    // Exclusion was a flag per value; the codec expresses it as the `!` prefix it already parses.
    const marked = suggestion.exclude && typeof value === 'string' ? `!${value}` : value;
    grouped.set(suggestion.key, [...(grouped.get(suggestion.key) ?? []), marked]);
  }

  return Object.fromEntries(
    Array.from(grouped, ([key, values]) => [
      key,
      // A single value stays a scalar, as the codec writes it; only a list of them becomes a list,
      // and a list has no room for a boolean (a boolean field is one flag).
      values.length === 1 ? values[0] : values.filter(value => typeof value === 'string'),
    ]),
  );
}

/**
 * Named filter sets for the pill bar, replacing the `savedFilters` setting for the locations that
 * have moved to it. A view is the bar's own two models (`matches` + `params`), so it can carry the
 * param-bound pills that the old `Suggestion[][]` shape had no way to express.
 *
 * Legacy entries for this location are converted on first use, once, and the old key is deleted in
 * the same write. Clearing it is the idempotency marker: nothing to convert means nothing happens,
 * so a view deleted afterwards cannot come back. This is deliberately not a schema migration,
 * since one location moving would otherwise version every frontend setting, and every later table
 * would add another version to the chain.
 */
export function useSavedViews(location: MaybeRefOrGetter<SavedFilterLocation>): SavedViewsReturn {
  const { updateFrontendSetting } = useSettingsOperations();

  const allViews = useSetting('savedViews');
  const allFilters = useSetting('savedFilters');

  const { t } = useI18n({ useScope: 'global' });

  const views = computed<SavedView[]>(() => get(allViews)[toValue(location)] ?? []);

  let converting = false;

  async function writeViews(next: SavedView[]): Promise<ActionStatus> {
    return updateFrontendSetting({
      savedViews: { ...get(allViews), [toValue(location)]: next },
    });
  }

  async function addView(name: string, state: SavedViewState): Promise<ActionStatus> {
    const trimmed = name.trim();
    const current = get(views);

    if (trimmed.length === 0) {
      return {
        message: t('table_filter.saved_views.errors.name_required'),
        success: false,
      };
    }

    if (current.length >= LIMIT_PER_LOCATION) {
      return {
        message: t('table_filter.saved_views.errors.limit', { limit: LIMIT_PER_LOCATION }),
        success: false,
      };
    }

    if (current.some(view => view.name.toLowerCase() === trimmed.toLowerCase())) {
      return {
        message: t('table_filter.saved_views.errors.duplicate'),
        success: false,
      };
    }

    return writeViews([...current, { matches: state.matches, name: trimmed, params: state.params }]);
  }

  async function deleteView(index: number): Promise<ActionStatus> {
    const next = get(views).slice();
    next.splice(index, 1);
    return writeViews(next);
  }

  /**
   * Moves this location's legacy `savedFilters` entries over, once.
   *
   * Both settings are written in one call: the conversion has to be atomic, or a failure between
   * the two would either lose the filters or convert them twice.
   *
   * ⭐ Called when the views UI is opened, deliberately NOT when the composable mounts. Every
   * frontend setting is stored as one blob, and a write sends `{...store, ...patch}`, so two
   * writers whose requests overlap lose the earlier one's keys. Logging in fires a burst of such
   * writes (the notification schedule, the last password confirmation), and a conversion running
   * on mount lands in the middle of it: verified in the app, where the converted views appeared in
   * the UI while the backend kept the legacy key, because a later write built from a snapshot
   * taken before the conversion's response had landed. Opening a menu is a deliberate act, seconds
   * away from that burst.
   */
  async function ensureConverted(): Promise<void> {
    const key = toValue(location);
    const legacy = get(allFilters)[key] ?? [];
    // The write clears the legacy key, which is what stops this from running twice, so a second
    // trigger arriving while it is still in flight has to be held off.
    if (legacy.length === 0 || converting)
      return;
    converting = true;

    const existing = get(views);
    const room = Math.max(LIMIT_PER_LOCATION - existing.length, 0);
    // The old filters had no names, so each gets a generated one the user can recognise by its
    // pill summary and rename by re-saving.
    const converted = legacy.slice(0, room).map((suggestions, index) => ({
      matches: matchesFromSuggestions(suggestions),
      name: t('table_filter.saved_views.converted_name', { number: existing.length + index + 1 }),
      // The old shape could not express a param-bound filter, so there is nothing to carry.
      params: {},
    }));

    const remaining = { ...get(allFilters) };
    delete remaining[key];

    try {
      await updateFrontendSetting({
        savedFilters: remaining,
        savedViews: { ...get(allViews), [key]: [...existing, ...converted] },
      });
    }
    finally {
      converting = false;
    }
  }

  return { addView, deleteView, ensureConverted, views };
}
