import type { ActiveFilter, FieldDef, FilterOp } from '@/modules/core/table/pill/core/types';
import { FilterOps, FilterValueTypes, type MatchedKeywordWithBehaviour } from '@/modules/core/table/filtering';
import { stateFromMatches } from '@/modules/core/table/pill/core/codec';
import { isDefaultOp, type OperatorLabels } from '@/modules/core/table/pill/core/operators';
import { resolveText } from '@/modules/core/table/pill/core/text';

/** The operator to show on a pill, or `undefined` when it is the field's default (hidden). */
export function pillOperator(field: FieldDef, filter: ActiveFilter): FilterOp | undefined {
  return isDefaultOp(field, filter.op) ? undefined : filter.op;
}

const LOWER_ONLY_OPS = new Set<FilterOp>([FilterOps.GT, FilterOps.AFTER]);
const UPPER_ONLY_OPS = new Set<FilterOp>([FilterOps.LT, FilterOps.BEFORE]);

function formatBound(field: FieldDef, value?: string): string | undefined {
  if (value === undefined)
    return undefined;
  return field.formatBound ? field.formatBound(value) : value;
}

/**
 * Renders a pair of bounds as the text beside the operator on a pill.
 *
 * @remarks
 * A single-bound operator shows only its own bound, so the value agrees with the operator label:
 * a "greater than" pill reads as `50` alone, never as "50 - 100". Under a two-bound operator with one
 * bound filled, the summary becomes that bound rather than a range with a hole in it, since
 * "01/07/2026 - " says nothing about which end is missing.
 */
function boundsSummary(field: FieldDef, op: FilterOp, lower?: string, upper?: string): string {
  const lo = formatBound(field, lower);
  const hi = formatBound(field, upper);
  if (LOWER_ONLY_OPS.has(op))
    return lo ?? '';
  if (UPPER_ONLY_OPS.has(op))
    return hi ?? '';
  if (!lo && !hi)
    return '';
  if (!hi)
    return `≥ ${lo}`;
  if (!lo)
    return `≤ ${hi}`;
  return `${lo} - ${hi}`;
}

function rangeSummary(field: FieldDef, filter: ActiveFilter): string {
  return boundsSummary(field, filter.op, filter.range?.min, filter.range?.max);
}

function dateSummary(field: FieldDef, filter: ActiveFilter): string {
  if (filter.date?.preset)
    return filter.date.preset;
  return boundsSummary(field, filter.op, filter.date?.from, filter.date?.to);
}

function valuesSummary(field: FieldDef, values: string[]): string {
  if (values.length === 0)
    return '';
  const labels = field.resolveLabel ? values.map(value => field.resolveLabel!(value)) : values;
  if (labels.length <= 2)
    return labels.join(', ');
  return `${labels[0]} +${labels.length - 1}`;
}

/**
 * Muted secondary text for a single-value pill (e.g. an account's address under its name).
 * Empty for multi-value pills (no room) or fields without a caption resolver.
 */
export function pillValueCaption(field: FieldDef, filter: ActiveFilter): string {
  if (!field.resolveCaption || field.captionScope === 'list' || filter.values.length !== 1)
    return '';
  return field.resolveCaption(filter.values[0]) ?? '';
}

/**
 * Describes a whole stored filter set in one line, for a saved view's row.
 *
 * @remarks
 * Read from the transported form, since that is what a view stores, so the fields decide what a
 * view means exactly as they do for the live bar.
 */
export function pillStateSummary(
  matches: MatchedKeywordWithBehaviour<string>,
  params: Record<string, unknown>,
  fields: FieldDef[],
  operatorLabels: OperatorLabels,
): string {
  return stateFromMatches(matches, params, fields)
    .map((filter) => {
      const field = fields.find(candidate => candidate.key === filter.fieldKey);
      if (!field)
        return '';
      const op = pillOperator(field, filter);
      const value = pillValueSummary(field, filter);
      const label = resolveText(field.label);
      const name = op ? `${label} ${operatorLabels[op]}` : label;
      // A boolean field has no value of its own: being present is the whole filter.
      return value ? `${name}: ${value}` : name;
    })
    .filter(entry => entry.length > 0)
    .join(' · ');
}

/**
 * A compact, presentation-only summary of a filter's values, shown on the pill.
 *
 * @remarks
 * This is the raw form. Resolving an identifier to something displayable, an asset to its symbol
 * say, is layered on by the bar.
 */
export function pillValueSummary(field: FieldDef, filter: ActiveFilter): string {
  switch (field.valueType) {
    case FilterValueTypes.BOOLEAN:
      return '';
    case FilterValueTypes.RANGE:
      return rangeSummary(field, filter);
    case FilterValueTypes.DATE:
      return dateSummary(field, filter);
    case FilterValueTypes.ENUM:
    case FilterValueTypes.ASSET:
      return valuesSummary(field, filter.values);
  }
}
