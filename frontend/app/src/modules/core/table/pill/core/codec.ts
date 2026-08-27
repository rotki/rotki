import type { ActiveFilter, FieldDef, FilterOp, FilterState } from '@/modules/core/table/pill/core/types';
import { arrayify } from '@/modules/core/common/data/array';
import { FilterBehaviours, type FilterObjectWithBehaviour, FilterOps, FilterValueTypes, type MatchedKeyword, type MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';

/**
 * The pure bridge between the `ActiveFilter[]` editing model and the transported form.
 *
 * @remarks
 * The emitted `matches` object keeps the exact shape `TableFilter` produces, so consumers and the
 * URL are unaffected: `!`-prefixed exclusion, `keyValue` keys, an asset carried as its identifier
 * and a boolean as `true`. Param-bound fields, such as the history account `locationLabels`, are
 * routed instead into a separate `params` bag keyed by their param key, ready for a
 * `useServerTable` param source.
 *
 * Scope: `enum` / `asset` / `boolean` value types + binding routing. `range` / `date`
 * collapse lands with the events-filter rewrite, when the field carries its wire-key mapping.
 *
 * @packageDocumentation
 */

/** The transported form of a filter state: filter-bound `matches` + param-bound `params`. */
export interface SerializedState {
  matches: Partial<MatchedKeyword<string>>;
  params: Record<string, string | string[] | boolean>;
}

type WireValue = string | string[] | boolean;

function buildLookup(fields: FieldDef[]): (key: string) => FieldDef | undefined {
  const byKey = new Map(fields.map(field => [field.key, field]));
  return (key: string): FieldDef | undefined => byKey.get(key);
}

function isBehaviourWrapped(value: unknown): value is FilterObjectWithBehaviour<string | string[] | boolean> {
  return typeof value === 'object' && value !== null && !Array.isArray(value) && 'values' in value;
}

/**
 * Writes one serialized value into the half of the transported form its field is bound to.
 *
 * @remarks
 * A param-bound boolean stays a boolean, because it is consumed as one (a toggle's model, a request
 * flag); stringifying it to `'true'` would make every reader parse it back.
 */
function writeTarget(field: FieldDef, target: SerializedState, value: WireValue): void {
  if (field.binding.kind === 'param') {
    target.params[field.binding.paramKey] = typeof value === 'boolean' || Array.isArray(value) ? value : String(value);
  }
  else {
    target.matches[field.key] = value;
  }
}

/** The raw (un-serialized) lower/upper bound values a range/date filter holds. */
function rawBounds(field: FieldDef, filter: ActiveFilter): { lower?: string; upper?: string } {
  if (field.valueType === FilterValueTypes.RANGE)
    return { lower: filter.range?.min, upper: filter.range?.max };
  return { lower: filter.date?.from, upper: filter.date?.to };
}

/**
 * Serializes a collapsed range/date filter into its two wire keys. The operator gates which
 * bounds are written (mirrors the editors hiding the min field on `lt`/`before` and the max on
 * `gt`/`after`), so a stale hidden value never leaks and the operator round-trips from the keys
 * that end up present.
 */
function writeBounds(field: FieldDef, target: SerializedState, filter: ActiveFilter): void {
  if (!field.bounds || field.binding.kind === 'param')
    return;

  const raw = rawBounds(field, filter);
  const serialize = (value?: string): string | undefined => {
    if (value === undefined || value === '')
      return undefined;
    const out = field.serializer ? field.serializer(value) : value;
    return out.length > 0 ? out : undefined;
  };

  const wantLower = filter.op !== FilterOps.LT && filter.op !== FilterOps.BEFORE;
  const wantUpper = filter.op !== FilterOps.GT && filter.op !== FilterOps.AFTER;

  const lower = wantLower ? serialize(raw.lower) : undefined;
  const upper = wantUpper ? serialize(raw.upper) : undefined;

  if (lower !== undefined)
    target.matches[field.bounds.lower] = lower;
  if (upper !== undefined)
    target.matches[field.bounds.upper] = upper;
}

/** Serializes the enum/asset value list, applying `!` exclusion markers where allowed. */
function writeEnumLike(field: FieldDef, target: SerializedState, filter: ActiveFilter): void {
  const exclude = filter.op === FilterOps.IS_NOT && field.allowExclusion;
  const values = filter.values
    .map(value => (field.serializer ? field.serializer(value) : value))
    .filter(value => value.length > 0)
    .map(value => (exclude ? `!${value}` : value));

  if (values.length === 0)
    return;

  writeTarget(field, target, field.multiple ? values : values[0]);
}

function anyFilled(...values: (string | undefined)[]): boolean {
  return values.some(value => value !== undefined && value.length > 0);
}

/**
 * Whether this filter would put anything on the wire, i.e. whether it filters at all.
 *
 * A field picked and then abandoned leaves a pill holding nothing: it changes no request and shows
 * no value, so it is a control the user has to clean up by hand. The bar drops such a pill when its
 * editor closes, and asks here rather than guessing per value type, so "empty" means exactly what
 * the serializer already means by it.
 */
export function hasWritableValue(field: FieldDef, filter: ActiveFilter): boolean {
  // An empty string is as absent as a missing one: a bound the user cleared holds one.
  const { date = {}, range = {}, values } = filter;

  switch (field.valueType) {
    // Presence is the whole value: a boolean field is on once it has been added.
    case FilterValueTypes.BOOLEAN:
      return true;
    case FilterValueTypes.RANGE:
      return anyFilled(range.min, range.max);
    case FilterValueTypes.DATE:
      return anyFilled(date.preset, date.from, date.to);
    case FilterValueTypes.ENUM:
    case FilterValueTypes.ASSET:
      return anyFilled(...values);
  }
}

/** Converts `ActiveFilter[]` into the transported form, dropping fields with no usable value. */
export function matchesFromState(state: FilterState, fields: FieldDef[]): SerializedState {
  const lookup = buildLookup(fields);
  const result: SerializedState = { matches: {}, params: {} };

  for (const filter of state) {
    const field = lookup(filter.fieldKey);
    if (!field)
      continue;

    if (field.valueType === FilterValueTypes.BOOLEAN)
      writeTarget(field, result, true);
    else if (field.valueType === FilterValueTypes.RANGE || field.valueType === FilterValueTypes.DATE)
      writeBounds(field, result, filter);
    else if (field.valueType === FilterValueTypes.ENUM || field.valueType === FilterValueTypes.ASSET)
      writeEnumLike(field, result, filter);
  }

  return result;
}

function decodeEnumLike(field: FieldDef, raw: unknown): ActiveFilter | undefined {
  let exclude = false;
  let source: unknown = raw;
  if (isBehaviourWrapped(raw)) {
    exclude = raw.behaviour === FilterBehaviours.EXCLUDE;
    source = raw.values;
  }

  const values: string[] = [];
  for (const item of arrayify(source)) {
    if (typeof item !== 'string')
      continue;
    let value = item;
    if (field.allowExclusion && value.startsWith('!')) {
      exclude = true;
      value = value.slice(1);
    }
    if (value.length > 0)
      values.push(field.deserializer ? field.deserializer(value) : value);
  }

  if (values.length === 0)
    return undefined;

  return { fieldKey: field.key, op: exclude ? FilterOps.IS_NOT : FilterOps.IS, values };
}

/** The operator implied by which bounds survived on the wire (see `writeBounds`). */
function opFromBounds(field: FieldDef, hasLower: boolean, hasUpper: boolean): FilterOp {
  if (hasLower && hasUpper)
    return FilterOps.BETWEEN;
  if (field.valueType === FilterValueTypes.RANGE)
    return hasLower ? FilterOps.GT : FilterOps.LT;
  return hasLower ? FilterOps.AFTER : FilterOps.BEFORE;
}

/** Rebuilds a collapsed range/date filter from its two wire keys. */
function decodeBounds(field: FieldDef, matches: MatchedKeywordWithBehaviour<string>): ActiveFilter | undefined {
  if (!field.bounds)
    return undefined;

  const read = (key: string): string | undefined => {
    const value = matches[key];
    if (typeof value !== 'string' || value.length === 0)
      return undefined;
    return field.deserializer ? field.deserializer(value) : value;
  };

  const lower = read(field.bounds.lower);
  const upper = read(field.bounds.upper);
  if (lower === undefined && upper === undefined)
    return undefined;

  const op = opFromBounds(field, lower !== undefined, upper !== undefined);

  if (field.valueType === FilterValueTypes.RANGE) {
    const range: { min?: string; max?: string } = {};
    if (lower !== undefined)
      range.min = lower;
    if (upper !== undefined)
      range.max = upper;
    return { fieldKey: field.key, op, range, values: [] };
  }

  const date: { from?: string; to?: string } = {};
  if (lower !== undefined)
    date.from = lower;
  if (upper !== undefined)
    date.to = upper;
  return { date, fieldKey: field.key, op, values: [] };
}

function decodeField(field: FieldDef, raw: unknown): ActiveFilter | undefined {
  if (raw === undefined || raw === null)
    return undefined;
  if (field.valueType === FilterValueTypes.BOOLEAN)
    return raw ? { fieldKey: field.key, op: FilterOps.IS, values: [] } : undefined;
  if (field.valueType !== FilterValueTypes.ENUM && field.valueType !== FilterValueTypes.ASSET)
    return undefined;
  return decodeEnumLike(field, raw);
}

/**
 * Converts the transported form back into `ActiveFilter[]`.
 *
 * @remarks
 * Reads each field from `matches` when it is filter-bound and from `params` when it is param-bound,
 * decoding `!`-prefixed and behaviour-wrapped exclusion into the field-level `is_not` operator.
 * Iterates `fields` rather than the payload, so the output order is stable.
 */
export function stateFromMatches(
  matches: MatchedKeywordWithBehaviour<string>,
  params: Record<string, unknown>,
  fields: FieldDef[],
): FilterState {
  const state: ActiveFilter[] = [];
  for (const field of fields) {
    if (field.valueType === FilterValueTypes.RANGE || field.valueType === FilterValueTypes.DATE) {
      const filter = decodeBounds(field, matches);
      if (filter)
        state.push(filter);
      continue;
    }

    const raw = field.binding.kind === 'param' ? params[field.binding.paramKey] : matches[field.key];
    const filter = decodeField(field, raw);
    if (filter)
      state.push(filter);
  }
  return state;
}
