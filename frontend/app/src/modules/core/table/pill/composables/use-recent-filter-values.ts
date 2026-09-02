import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { startPromise } from '@shared/utils';
import { useSetting } from '@/modules/settings/use-setting';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

/** Values kept per field. Enough to cover the handful a user actually returns to. */
const MAX_PER_FIELD = 10;

/**
 * Longest value worth remembering. A notes filter can hold an arbitrarily long substring, and the
 * whole bucket rides in one settings blob that every login fetches, so an unbounded value would
 * bloat it. Anything longer is simply not remembered.
 */
const MAX_VALUE_LENGTH = 120;

interface RecentFilterValuesReturn {
  /** Most recent first, for a free-text field. Other fields have their own option list. */
  recentFor: (field: FieldDef) => string[];
  /** Records values a user committed, newest first and each value once, capped per field. */
  remember: (field: FieldDef, values: string[]) => void;
}

/**
 * Remembers what was typed into the free-text filter fields (tx hash, address, validator, notes),
 * so returning to a value does not mean retyping it: those fields have no option list of their
 * own, which is exactly why they had nothing to suggest.
 *
 * Kept in the per-user frontend settings rather than local storage. These are addresses,
 * transaction hashes and note fragments, so they belong with the user's own settings and not in
 * plaintext on a machine other users share.
 */
export function useRecentFilterValues(): RecentFilterValuesReturn {
  const { updateFrontendSetting } = useSettingsOperations();
  const recentValues = useSetting('recentFilterValues');

  function recentFor(field: FieldDef): string[] {
    if (!field.freeText)
      return [];
    return (get(recentValues)[field.key] ?? []).map(entry => entry.value);
  }

  function remember(field: FieldDef, values: string[]): void {
    if (!field.freeText)
      return;

    const worthKeeping = values.filter(value => value.length > 0 && value.length <= MAX_VALUE_LENGTH);
    if (worthKeeping.length === 0)
      return;

    const current = get(recentValues)[field.key] ?? [];
    const countOf = (value: string): number => (current.find(entry => entry.value === value)?.count ?? 0) + 1;

    const next = [
      ...worthKeeping.slice().reverse().map(value => ({ count: countOf(value), value })),
      ...current.filter(entry => !worthKeeping.includes(entry.value)),
    ].slice(0, MAX_PER_FIELD);

    startPromise(updateFrontendSetting({
      recentFilterValues: { ...get(recentValues), [field.key]: next },
    }));
  }

  return { recentFor, remember };
}
