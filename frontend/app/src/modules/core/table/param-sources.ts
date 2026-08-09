import type { MaybeRefOrGetter } from 'vue';
import type { LocationQuery } from '@/modules/core/table/route';
import { nonEmptyProperties } from '@/modules/core/common/data/data';
import { FilterBehaviours, type FilterObjectWithBehaviour } from '@/modules/core/table/filtering';

type FilterValue = string | string[] | boolean | FilterObjectWithBehaviour<string | string[] | boolean>;

/** Where a param source contributes its values. */
export type ParamDestination = 'request' | 'url' | 'both';

/**
 * One contributor to the request payload and/or the URL query.
 *
 * Replaces the five overlapping bags (`defaultParams`, `extraParams`,
 * `requestParams`, `queryParamsOnly`, `locationOverview`) which differed only in
 * destination and precedence. Precedence is list order: later sources win, and
 * every non-`base` source wins over the filter.
 */
export interface ParamSource {
  /**
   * `object` rather than `Record<string, unknown>` on purpose: TypeScript does not
   * give interfaces an implicit index signature, so the narrower type would force
   * every consumer to abandon its named param interface for an inline type.
   */
  values: MaybeRefOrGetter<object>;
  to: ParamDestination;
  /**
   * The read direction: parses the raw query back into this source's state,
   * whenever URL state is (re)applied. It sits beside `values` so the two halves of
   * each key stay in one object and cannot drift apart, which is what the old
   * standalone `onRouteQuery` option (matched to its source by hand) allowed. Takes
   * the whole query rather than a single key, because a source may fold several keys
   * onto one ref, or write several refs from one query.
   */
  fromQuery?: (query: LocationQuery) => void;
  /**
   * Drop empty values from the *request* contribution. URL contributions are
   * always stripped, so this only affects `to: 'request' | 'both'`.
   */
  skipEmpty?: boolean;
  /**
   * Values the filter overrides. The old `defaultParams` was the only bag the
   * filter could win against, and this is what it became.
   */
  isDefault?: boolean;
}

function stringifyValues(values: object): Record<string, unknown> {
  return Object.fromEntries(Object.entries(values).map(([key, value]) => [key, value?.toString()]));
}

function contributes(source: ParamSource, destination: 'request' | 'url'): boolean {
  return source.to === 'both' || source.to === destination;
}

function contribution(source: ParamSource, destination: 'request' | 'url'): object {
  const values = toValue(source.values);

  // URL values are always stringified first and then stripped: an empty array has
  // to become '' before `removeEmptyString` can drop it. Stripping first would
  // leave `[]` in the query as an empty param.
  if (destination === 'url')
    return nonEmptyProperties(stringifyValues(values), { removeEmptyString: true });

  return source.skipEmpty ? nonEmptyProperties(values) : values;
}

export function collectSources(
  sources: ParamSource[],
  destination: 'request' | 'url',
  predicate: (source: ParamSource) => boolean = (): boolean => true,
): Record<string, unknown> {
  const merged: Record<string, unknown> = {};
  for (const source of sources) {
    if (!contributes(source, destination) || !predicate(source))
      continue;

    Object.assign(merged, contribution(source, destination));
  }
  return merged;
}

/**
 * Runs the read direction of every source that declares one, pulling the raw query
 * back into their bound state. Replaces the single top-level `onRouteQuery` hook.
 */
export function applySourceReads(sources: ParamSource[], query: LocationQuery): void {
  for (const source of sources)
    source.fromQuery?.(query);
}

/** The filter overrides `isDefault` sources and loses to every other one. */
export function mergeParams(
  sources: ParamSource[],
  destination: 'request' | 'url',
  filterValues: object,
): Record<string, unknown> {
  return {
    ...collectSources(sources, destination, source => !!source.isDefault),
    ...filterValues,
    ...collectSources(sources, destination, source => !source.isDefault),
  };
}

/**
 * Resolves a leading `!` into an EXCLUDE behaviour, stripping it from the string
 * or from every array element. Only called for keys the table declares as
 * behaviour-carrying, which is what makes the prefix meaningful.
 */
function resolveExclusion(
  data: string | string[] | boolean,
): { exclude: boolean; values: string | string[] | boolean } {
  if (typeof data === 'string' && data.startsWith('!'))
    return { exclude: true, values: data.substring(1) };

  if (Array.isArray(data) && data.length > 0 && data[0].startsWith('!'))
    return { exclude: true, values: data.map(item => (item.startsWith('!') ? item.substring(1) : item)) };

  return { exclude: false, values: data };
}

/**
 * Builds the `{ behaviour, values }` pair for one key's value: an already-wrapped
 * value keeps (or defaults) its behaviour, a plain value is wrapped and resolved
 * for exclusion. Returns undefined when there is nothing to rewrite.
 */
function toBehaviourValue(
  data: FilterValue,
): FilterObjectWithBehaviour<string | string[] | boolean> | undefined {
  if (typeof data === 'object' && !Array.isArray(data)) {
    if (data.values)
      return { behaviour: data.behaviour ?? FilterBehaviours.INCLUDE, values: data.values };

    return undefined;
  }

  const { exclude, values } = resolveExclusion(data);
  return {
    behaviour: exclude ? FilterBehaviours.EXCLUDE : FilterBehaviours.INCLUDE,
    values,
  };
}

/** Whether a bag entry is something a filter can carry, and so something to rewrite. */
function isFilterValue(data: unknown): data is FilterValue {
  return typeof data === 'string' || typeof data === 'boolean' || Array.isArray(data)
    || (typeof data === 'object' && data !== null);
}

/**
 * Rewrites plain filter values into `{ behaviour, values }` pairs for the keys the table declares
 * as behaviour-carrying, resolving a leading `!` into an EXCLUDE behaviour.
 *
 * Takes and returns a plain bag rather than the table's filter type: by the time it is called the
 * filter has already been merged with the param sources, so the keys are no longer only the
 * filter's own. Typing it as the filter type only ever meant asserting that at the call site.
 */
export function transformFilters(
  filters: Record<string, unknown>,
  behaviourKeys: readonly string[],
): Record<string, unknown> {
  if (behaviourKeys.length === 0)
    return filters;

  const newFilters: Record<string, unknown> = { ...filters };

  behaviourKeys.forEach((key) => {
    const data = filters[key];
    if (!data || !isFilterValue(data))
      return;

    const value = toBehaviourValue(data);
    if (value !== undefined)
      newFilters[key] = value;
  });

  return newFilters;
}
