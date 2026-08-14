import type { AssetsWithId } from '@/modules/assets/types';
import type { FieldText } from '@/modules/core/table/pill/core/text';
import type { FieldDef, FilterOp, FilterValueType, TypedFilterDraft } from '@/modules/core/table/pill/core/types';
import { FilterOps, FilterValueTypes } from '@/modules/core/table/filtering';
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
 * alongside filter-bound fields. This is how history's account (`locationLabels`) and the
 * other external history filters are absorbed into the one bar.
 */
export interface ParamFieldSpec {
  readonly key: string;
  readonly label: FieldText;
  readonly paramKey: string;
  readonly to: 'request' | 'url' | 'both';
  readonly valueType?: FilterValueType;
  readonly operators?: readonly FilterOp[];
  readonly multiple?: boolean;
  /**
   * Typed rather than picked, the same as on a filter-bound field: a param-bound table can filter
   * on a keyword it has no list to offer for (the blockchain balances search over asset names).
   */
  readonly freeText?: boolean;
  readonly hint?: FieldText;
  readonly display?: FieldDef['display'];
  readonly excludes?: FieldDef['excludes'];
  readonly resolveIcon?: FieldDef['resolveIcon'];
  readonly resolveSwatch?: FieldDef['resolveSwatch'];
  readonly resolveLoading?: FieldDef['resolveLoading'];
  readonly fromLegacy?: FieldDef['fromLegacy'];
  readonly resolveLabel?: (value: string) => string;
  readonly resolveCaption?: (value: string) => string | undefined;
  readonly captionScope?: FieldDef['captionScope'];
  readonly resolveKeywords?: FieldDef['resolveKeywords'];
  readonly suggest?: () => string[];
  readonly searchAsset?: (value: string) => Promise<AssetsWithId>;
}

/**
 * A pair of scalar bound matchers (min/max amount, start/end date) collapsed into one
 * range/date field. `lowerKey`/`upperKey` are the wire keys the two bounds serialize to
 * (the codec routes `range.min`/`date.from` to `lowerKey`, `range.max`/`date.to` to `upperKey`).
 */
/**
 * A field bound to the table's filter bag, declared directly rather than through a matcher.
 *
 * The counterpart of `ParamFieldSpec` for the other binding. A matcher exists to describe a field
 * to the old text bar, which no longer exists, so a table feeding only the pill bar has no reason
 * to build one: everything the bar actually reads is declared here.
 */
export interface MatchFieldSpec {
  readonly key: string;
  readonly label: FieldText;
  readonly admits?: FieldDef['admits'];
  readonly valueType?: FilterValueType;
  readonly operators?: readonly FilterOp[];
  readonly multiple?: boolean;
  readonly allowExclusion?: boolean;
  /** Typed rather than picked: the value is whatever the user writes. */
  readonly freeText?: boolean;
  readonly hint?: FieldText;
  /** Shown when `validate` rejects what was typed, in place of the generic message. */
  readonly invalidHint?: FieldText;
  readonly validate?: (value: string) => boolean;
  readonly suggest?: () => string[];
  readonly searchAsset?: (value: string) => Promise<AssetsWithId>;
  readonly serializer?: (value: string) => string;
  readonly deserializer?: (value: string) => string;
  readonly display?: FieldDef['display'];
  readonly excludes?: FieldDef['excludes'];
  readonly resolveIcon?: FieldDef['resolveIcon'];
  readonly resolveLabel?: (value: string) => string;
  readonly resolveCaption?: (value: string) => string | undefined;
  readonly captionScope?: FieldDef['captionScope'];
  readonly resolveKeywords?: FieldDef['resolveKeywords'];
  readonly resolveLoading?: FieldDef['resolveLoading'];
}

export interface BoundsFieldSpec {
  readonly key: string;
  readonly label: FieldText;
  readonly lowerKey: string;
  readonly upperKey: string;
  readonly hint?: FieldText;
  readonly operators?: readonly FilterOp[];
}

/** A date field additionally carries the display <-> wire (timestamp) serializers for each bound. */
export interface DateFieldSpec extends BoundsFieldSpec {
  readonly serializer?: (value: string) => string;
  readonly deserializer?: (value: string) => string;
  readonly formatBound?: (value: string) => string;
  /** See {@link FieldDef.allowEqualBounds}. Defaults to allowed. */
  readonly allowEqualBounds?: boolean;
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
    binding: { kind: 'filter' },
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
    allowEqualBounds: spec.allowEqualBounds ?? true,
    allowExclusion: false,
    binding: { kind: 'filter' },
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

function operatorsOf(valueType: FilterValueType, operators?: readonly FilterOp[]): readonly FilterOp[] {
  return operators && operators.length > 0 ? operators : DEFAULT_OPERATORS[valueType];
}

/**
 * Which operators a declared filter-bag field offers. `is_not` is offered only when the field
 * declares `allowExclusion`, because the codec writes the `!` negation only for such a field
 * (`codec.ts`): offering it otherwise gives the user an operator that silently applies as `is`.
 *
 * The value-type defaults cannot be used directly here — they list `is_not` for every enum and
 * asset, which is what a field may express once its table declares the key as behaviour-carrying,
 * not what it can express today.
 */
function matchFieldOperators(
  valueType: FilterValueType,
  allowExclusion: boolean,
  operators?: readonly FilterOp[],
): readonly FilterOp[] {
  if (operators && operators.length > 0)
    return operators;
  if (valueType === FilterValueTypes.ENUM || valueType === FilterValueTypes.ASSET)
    return allowExclusion ? [FilterOps.IS, FilterOps.IS_NOT] : [FilterOps.IS];
  return DEFAULT_OPERATORS[valueType];
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
    captionScope: spec.captionScope,
    display: spec.display,
    excludes: spec.excludes,
    freeText: spec.freeText,
    hint: spec.hint,
    key: spec.key,
    label: spec.label,
    multiple: spec.multiple ?? true,
    operators: paramOperators(valueType, spec.operators),
    resolveCaption: spec.resolveCaption,
    resolveIcon: spec.resolveIcon,
    resolveKeywords: spec.resolveKeywords,
    resolveLabel: spec.resolveLabel,
    fromLegacy: spec.fromLegacy,
    resolveLoading: spec.resolveLoading,
    resolveSwatch: spec.resolveSwatch,
    searchAsset: spec.searchAsset,
    suggest: spec.suggest,
    valueType,
  };
}

/**
 * Declares a field that writes into the table's filter bag, without a matcher behind it.
 *
 * The replacement for `toFieldDef`: same output, but the table states what the field is instead of
 * describing it to a bar that was deleted and having it translated.
 */
export function toMatchFieldDef(spec: MatchFieldSpec): FieldDef {
  const valueType = spec.valueType ?? FilterValueTypes.ENUM;
  const allowExclusion = spec.allowExclusion ?? false;
  return {
    admits: spec.admits,
    allowExclusion,
    binding: { kind: 'filter' },
    captionScope: spec.captionScope,
    deserializer: spec.deserializer,
    display: spec.display,
    excludes: spec.excludes,
    freeText: spec.freeText,
    hint: spec.hint,
    invalidHint: spec.invalidHint,
    key: spec.key,
    label: spec.label,
    multiple: spec.multiple ?? false,
    operators: matchFieldOperators(valueType, allowExclusion, spec.operators),
    resolveCaption: spec.resolveCaption,
    resolveIcon: spec.resolveIcon,
    resolveKeywords: spec.resolveKeywords,
    resolveLabel: spec.resolveLabel,
    resolveLoading: spec.resolveLoading,
    searchAsset: spec.searchAsset,
    serializer: spec.serializer,
    suggest: spec.suggest,
    validate: spec.validate,
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
