import type { FieldDef, FilterOp, FilterValueType } from '@/modules/core/table/pill/core/types';
import { FilterOps, FilterValueTypes } from '@/modules/core/table/filtering';

/** Default operator sets per value type, most-default first. */
export const DEFAULT_OPERATORS: Record<FilterValueType, readonly FilterOp[]> = {
  [FilterValueTypes.ASSET]: [FilterOps.IS, FilterOps.IS_NOT],
  [FilterValueTypes.BOOLEAN]: [FilterOps.IS],
  [FilterValueTypes.DATE]: [FilterOps.BETWEEN, FilterOps.AFTER, FilterOps.BEFORE],
  [FilterValueTypes.ENUM]: [FilterOps.IS, FilterOps.IS_NOT],
  [FilterValueTypes.RANGE]: [FilterOps.BETWEEN, FilterOps.GT, FilterOps.LT],
};

/**
 * Already-translated label per operator, supplied by the Vue layer.
 *
 * The core cannot translate: it has no locale and no `t`. It used to carry English strings with a
 * note that the component layer would resolve them, which nothing did, so every non-English user
 * read `is not` and `greater than` on their pills.
 */
export type OperatorLabels = Record<FilterOp, string>;

/** The operators a field allows, never empty (falls back to the value-type defaults). */
export function operatorsFor(field: FieldDef): readonly FilterOp[] {
  return field.operators.length > 0 ? field.operators : DEFAULT_OPERATORS[field.valueType];
}

/** The default operator for a field: the first allowed one. Hidden on the pill. */
export function defaultOp(field: FieldDef): FilterOp {
  return operatorsFor(field)[0];
}

/** Whether an operator is the field's default, so the pill can hide it. */
export function isDefaultOp(field: FieldDef, op: FilterOp): boolean {
  return op === defaultOp(field);
}
