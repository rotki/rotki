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

function boundsSummary(field: FieldDef, op: FilterOp, lower?: string, upper?: string): string {
  const lo = formatBound(field, lower);
  const hi = formatBound(field, upper);
  // Single-bound operators show only their bound, so the value matches the operator label (a
  // "greater than" pill reads "> 50", never "50 - 100").
  if (LOWER_ONLY_OPS.has(op))
    return lo ?? '';
  if (UPPER_ONLY_OPS.has(op))
    return hi ?? '';
  if (!lo && !hi)
    return '';
  // Only one bound filled under a two-bound operator: read it as that bound rather than as a
  // range with a hole in it ("01/07/2026 - ..." says nothing about which end is missing).
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
  if (!field.resolveCaption || filter.values.length !== 1)
    return '';
  return field.resolveCaption(filter.values[0]) ?? '';
}

/**
 * One line describing a whole stored filter set, for a saved view's row: every field it holds with
 * its value summary. Read from the transported form, since that is what a view stores, so the
 * fields decide what a view means exactly as they do for the live bar. A filter naming a field the
 * table no longer has is dropped by the decoder, so a stale view degrades to what still applies.
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
 * A compact, presentation-only summary of a filter's value(s), shown on the pill. Display
 * resolution (e.g. asset identifier -> symbol) is layered on by the bar; this is the raw form.
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
