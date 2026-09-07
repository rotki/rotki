import type { Ref } from 'vue';
import type { LocationQuery } from 'vue-router';
import { objectKeys } from '@/modules/core/common/data/array';
import { firstQueryValue } from '@/modules/core/table/route';

/** A filter bag value: the pill bar types every key as one-or-many, and some keys are toggles. */
type FilterValue = string | string[] | number | number[] | boolean | undefined;

interface UseMappingAdminOptions<T extends object, TFilters extends Record<string, FilterValue>> {
  /** A blank mapping, before any seeding. */
  blank: () => T;
  /** The pill-bar filter the table is currently narrowed to. */
  filter: Ref<TFilters>;
  /**
   * Mapping fields seeded from the filter, as field name to filter key.
   *
   * @remarks
   * Adding while narrowed to an exchange should not ask for that exchange again.
   */
  seedFromFilter: Partial<Record<keyof T, keyof TFilters>>;
  /** Mapping fields seeded from the `?add=` query, as field name to query parameter. */
  seedFromQuery: Partial<Record<keyof T, string>>;
}

interface UseMappingAdminReturn<T> {
  /**
   * Opens the dialog on a blank mapping seeded from the filter.
   *
   * @remarks
   * `payload` is applied last and wins, so a caller can override any seeded field.
   */
  add: (payload?: Partial<T>) => void;
  /**
   * Consumes an `?add=` query, opening the dialog seeded from its parameters.
   *
   * @remarks
   * The query is cleared first, so a reload does not reopen the dialog.
   *
   * @returns whether the query asked for the dialog
   */
  consumeAddQuery: () => Promise<boolean>;
  /** Opens the dialog on an existing mapping. */
  edit: (mapping: T) => void;
  /** Whether the dialog is editing rather than creating. */
  editMode: Readonly<Ref<boolean>>;
  /** The mapping the dialog is editing or creating, or undefined while it is closed. */
  modelValue: Ref<T | undefined>;
}

/**
 * The add-and-edit flow the asset-mapping admin pages share: a new mapping is seeded from whatever
 * the pill bar is narrowed to, and an `?add=` link seeds it from the url instead.
 *
 * @returns the dialog's mapping and the three ways it opens
 */
export function useMappingAdmin<T extends object, TFilters extends Record<string, FilterValue>>(
  options: UseMappingAdminOptions<T, TFilters>,
): UseMappingAdminReturn<T> {
  const { blank, filter, seedFromFilter, seedFromQuery } = options;

  const router = useRouter();
  const route = useRoute();

  const modelValue = ref<T>();
  const editMode = shallowRef<boolean>(false);

  function filterValue(key: keyof TFilters): string {
    const picked = get(filter)[key];
    return (Array.isArray(picked) ? picked[0] : picked)?.toString() ?? '';
  }

  function seededFromFilter(): Partial<T> {
    const seeded: Partial<T> = {};
    for (const field of objectKeys(seedFromFilter)) {
      const key = seedFromFilter[field];
      if (key !== undefined)
        Reflect.set(seeded, field, filterValue(key));
    }
    return seeded;
  }

  function seededFromQuery(query: LocationQuery): Partial<T> {
    const seeded: Partial<T> = {};
    for (const field of objectKeys(seedFromQuery)) {
      const param = seedFromQuery[field];
      if (param !== undefined)
        Reflect.set(seeded, field, firstQueryValue(query[param]));
    }
    return seeded;
  }

  function add(payload?: Partial<T>): void {
    set(modelValue, {
      ...blank(),
      ...seededFromFilter(),
      ...payload,
    });
    set(editMode, false);
  }

  function edit(mapping: T): void {
    set(modelValue, mapping);
    set(editMode, true);
  }

  async function consumeAddQuery(): Promise<boolean> {
    const { query } = get(route);
    if (!query.add)
      return false;

    await router.replace({ query: {} });
    add(seededFromQuery(query));
    return true;
  }

  return {
    add,
    consumeAddQuery,
    edit,
    editMode: readonly(editMode),
    modelValue,
  };
}
