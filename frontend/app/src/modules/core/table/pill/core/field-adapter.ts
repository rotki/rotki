import type { AssetsWithId } from '@/modules/assets/types';
import type { FieldBinding, FieldDef, FilterOp, FilterValueType, TypedFilterDraft } from '@/modules/core/table/pill/core/types';
import { FilterOps, FilterValueTypes, type SearchMatcher } from '@/modules/core/table/filtering';
import { DEFAULT_OPERATORS } from '@/modules/core/table/pill/core/operators';
import { parseDateQuery, parseRangeQuery, type ParseTimestamp } from '@/modules/core/table/pill/core/typed-filters';

/**
 * The pill editor a field renders in. `asset` is the dedicated asset picker (icon + symbol +
 * name, async search); everything else that is picked from a list, accounts included, is the
 * enum checklist, which draws each option from what its field resolves for the value.
 */
export type EditorKind = 'enum' | 'range' | 'date' | 'boolean' | 'asset' | 'text';

/**
 * An external (param-backed) filter described as a field, so the pill bar can render it
 * alongside matcher-backed fields. This is how history's account (`locationLabels`) and the
 * other external history filters are absorbed into the one bar.
 */
export interface ParamFieldSpec {
  readonly key: string;
  readonly label: string;
  readonly paramKey: string;
  readonly to: 'request' | 'url' | 'both';
  readonly valueType?: FilterValueType;
  readonly operators?: readonly FilterOp[];
  readonly multiple?: boolean;
  readonly hint?: string;
  readonly display?: FieldDef['display'];
  readonly excludes?: FieldDef['excludes'];
  readonly resolveIcon?: FieldDef['resolveIcon'];
  readonly resolveSwatch?: FieldDef['resolveSwatch'];
  readonly resolveLoading?: FieldDef['resolveLoading'];
  readonly resolveLabel?: (value: string) => string;
  readonly resolveCaption?: (value: string) => string | undefined;
  readonly resolveKeywords?: FieldDef['resolveKeywords'];
  readonly suggest?: () => string[];
  readonly searchAsset?: (value: string) => Promise<AssetsWithId>;
}

/**
 * A pair of scalar bound matchers (min/max amount, start/end date) collapsed into one
 * range/date field. `lowerKey`/`upperKey` are the wire keys the two bounds serialize to
 * (the codec routes `range.min`/`date.from` to `lowerKey`, `range.max`/`date.to` to `upperKey`).
 */
export interface BoundsFieldSpec {
  readonly key: string;
  readonly label: string;
  readonly lowerKey: string;
  readonly upperKey: string;
  readonly hint?: string;
  readonly operators?: readonly FilterOp[];
}

/** A date field additionally carries the display <-> wire (timestamp) serializers for each bound. */
export interface DateFieldSpec extends BoundsFieldSpec {
  readonly serializer?: (value: string) => string;
  readonly deserializer?: (value: string) => string;
  readonly formatBound?: (value: string) => string;
  /**
   * Reads a written date into a wire bound, so the bar can offer a date typed into it as a filter.
   * Injected because only the caller knows the user's date format. Omitted = the field offers
   * nothing for what is typed, which is how it behaved before.
   */
  readonly parseBound?: ParseTimestamp;
}

/** Collapses two amount matchers (min/max) into one numeric `range` field. */
export function toRangeFieldDef(spec: BoundsFieldSpec): FieldDef {
  return {
    allowExclusion: false,
    binding: { kind: 'matcher' },
    bounds: { lower: spec.lowerKey, upper: spec.upperKey },
    hint: spec.hint,
    key: spec.key,
    label: spec.label,
    multiple: false,
    operators: operatorsOf(FilterValueTypes.RANGE, spec.operators),
    // Every numeric field can read a typed amount; there is nothing table-specific about `>100`.
    parseTyped: parseRangeQuery,
    valueType: FilterValueTypes.RANGE,
  };
}

/** Collapses two period matchers (start/end) into one `date` field. */
export function toDateFieldDef(spec: DateFieldSpec): FieldDef {
  const { parseBound } = spec;
  return {
    allowExclusion: false,
    binding: { kind: 'matcher' },
    bounds: { lower: spec.lowerKey, upper: spec.upperKey },
    deserializer: spec.deserializer,
    formatBound: spec.formatBound,
    hint: spec.hint,
    key: spec.key,
    label: spec.label,
    multiple: false,
    operators: operatorsOf(FilterValueTypes.DATE, spec.operators),
    ...(parseBound ? { parseTyped: (query: string): TypedFilterDraft[] => parseDateQuery(query, parseBound) } : {}),
    serializer: spec.serializer,
    valueType: FilterValueTypes.DATE,
  };
}

/** Derives the value type from an explicit override, else the matcher discriminant. */
export function resolveValueType(matcher: SearchMatcher<string, string>): FilterValueType {
  if (matcher.valueType)
    return matcher.valueType;
  if ('asset' in matcher)
    return FilterValueTypes.ASSET;
  if ('boolean' in matcher)
    return FilterValueTypes.BOOLEAN;
  return FilterValueTypes.ENUM;
}

function operatorsOf(valueType: FilterValueType, operators?: readonly FilterOp[]): readonly FilterOp[] {
  return operators && operators.length > 0 ? operators : DEFAULT_OPERATORS[valueType];
}

/**
 * Which operators a matcher-backed field offers. `is_not` (the `!` negation) is offered only
 * when the field can express it — today that is a string matcher with `allowExclusion`. Adding
 * more operators later (range/date `gt`/`lt`/`between`/…) is just widening this list + teaching
 * the codec to serialize them; the pill reads it via `operatorsFor` and hides the default one.
 */
function matcherOperators(valueType: FilterValueType, matcher: SearchMatcher<string, string>): readonly FilterOp[] {
  if (matcher.operators && matcher.operators.length > 0)
    return matcher.operators;
  if (valueType === FilterValueTypes.ENUM || valueType === FilterValueTypes.ASSET) {
    const canExclude = 'string' in matcher && Boolean(matcher.allowExclusion);
    return canExclude ? [FilterOps.IS, FilterOps.IS_NOT] : [FilterOps.IS];
  }
  return DEFAULT_OPERATORS[valueType];
}

/** Normalizes a matcher into the presentation-facing `FieldDef`. */
export function toFieldDef(matcher: SearchMatcher<string, string>): FieldDef {
  const valueType = resolveValueType(matcher);
  const binding: FieldBinding = { kind: 'matcher' };
  return {
    allowExclusion: 'string' in matcher ? Boolean(matcher.allowExclusion) : false,
    binding,
    deserializer: 'string' in matcher ? matcher.deserializer : undefined,
    hint: matcher.hint,
    key: String(matcher.keyValue ?? matcher.key),
    label: matcher.description,
    multiple: Boolean(matcher.multiple),
    operators: matcherOperators(valueType, matcher),
    searchAsset: 'asset' in matcher ? matcher.suggestions : undefined,
    serializer: 'string' in matcher ? matcher.serializer : undefined,
    suggest: 'string' in matcher ? matcher.suggestions : undefined,
    validate: 'string' in matcher ? matcher.validate : undefined,
    valueType,
  };
}

/**
 * Which operators a param-backed field offers. A param carries a plain list of values, with no
 * form for the `!` negation the codec writes for an excluding matcher — hence `allowExclusion:
 * false` below. So `is_not` is not offered either: the chip would be inert, silently dropping
 * what the user asked for. Range/date keep their defaults; those are expressed by which bound is
 * sent, not by a prefix.
 */
function paramOperators(valueType: FilterValueType, operators?: readonly FilterOp[]): readonly FilterOp[] {
  if (operators && operators.length > 0)
    return operators;
  if (valueType === FilterValueTypes.ENUM || valueType === FilterValueTypes.ASSET)
    return [FilterOps.IS];
  return DEFAULT_OPERATORS[valueType];
}

/** Normalizes an external param filter into the same `FieldDef` shape. */
export function toParamFieldDef(spec: ParamFieldSpec): FieldDef {
  const valueType = spec.valueType ?? FilterValueTypes.ENUM;
  return {
    allowExclusion: false,
    binding: { kind: 'param', paramKey: spec.paramKey, to: spec.to },
    display: spec.display,
    excludes: spec.excludes,
    hint: spec.hint,
    key: spec.key,
    label: spec.label,
    multiple: spec.multiple ?? true,
    operators: paramOperators(valueType, spec.operators),
    resolveCaption: spec.resolveCaption,
    resolveIcon: spec.resolveIcon,
    resolveKeywords: spec.resolveKeywords,
    resolveLabel: spec.resolveLabel,
    resolveLoading: spec.resolveLoading,
    resolveSwatch: spec.resolveSwatch,
    searchAsset: spec.searchAsset,
    suggest: spec.suggest,
    valueType,
  };
}

/** The editor a field renders in. */
export function resolveEditor(field: FieldDef): EditorKind {
  if (field.freeText)
    return 'text';
  switch (field.valueType) {
    case FilterValueTypes.RANGE:
      return 'range';
    case FilterValueTypes.DATE:
      return 'date';
    case FilterValueTypes.BOOLEAN:
      return 'boolean';
    case FilterValueTypes.ASSET:
      return 'asset';
    case FilterValueTypes.ENUM:
      return 'enum';
  }
}
