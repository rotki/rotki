import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldText } from '@/modules/core/table/pill/core/text';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { toDateFieldDef } from '@/modules/core/table/pill/core/field-adapter';

/**
 * The two wire keys a period is sent as. Every table names them differently in its own key enum
 * (`start`/`end`, `fromTimestamp`/`toTimestamp`) but they are the same two bounds: the lower one is
 * inclusive from, the upper one inclusive to, both unix seconds.
 */
export interface PeriodFieldBounds {
  readonly lowerKey: string;
  readonly upperKey: string;
  /**
   * Whether the two bounds may name the same second. Allowed by default, which is what inclusive
   * second bounds mean. Set `false` for a table whose timestamp column is stored in milliseconds:
   * its bounds are scaled by 1000, so an equal pair asks for the single millisecond `X000` and
   * quietly drops every other event in that second.
   */
  readonly allowEqual?: boolean;
}

/**
 * The period pill, shared by every table that filters on a time range.
 *
 * Four tables collapsed their two date bounds into one pill and each spelled out the same call: the
 * bounds are stored as the timestamps they are sent as, and the date editor reads and writes them
 * through the user's configured date format. None of that is table-specific, so the only things a
 * table still says are what it calls the pill and which two keys the bounds serialize to.
 *
 * Deliberately no serializer: a table's own date serializers belong to the old text bar, where the
 * user typed a formatted date and it had to be converted on the way in.
 */
export function toPeriodField(label: FieldText, bounds: PeriodFieldBounds, resolvers: SharedFieldResolvers): FieldDef {
  return toDateFieldDef({
    allowEqualBounds: bounds.allowEqual ?? true,
    formatBound: resolvers.formatDate,
    key: 'period',
    label,
    lowerKey: bounds.lowerKey,
    parseBound: resolvers.parseDate,
    upperKey: bounds.upperKey,
  });
}
