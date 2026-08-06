import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { decorateSharedField, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { toDateFieldDef, toFieldDef } from '@/modules/core/table/pill/core/field-adapter';
import { InternalTxConflictFilterValueKeys, type Matcher } from '@/modules/history/internal-tx-conflicts/use-internal-tx-conflicts-filter';

type Translate = (key: string) => string;

/**
 * The pill-bar fields for the internal transaction conflicts table: the chain matcher, drawn as the
 * shared chain pill, plus the two date matchers folded into one `period` pill. The wire form is
 * unchanged — the bounds still serialize to `fromTimestamp`/`toTimestamp`.
 */
export function toInternalTxConflictFields(
  matchers: Matcher[],
  resolvers: SharedFieldResolvers,
  t: Translate,
): FieldDef[] {
  const { formatDate, parseDate } = resolvers;
  const result: FieldDef[] = [];

  for (const matcher of matchers) {
    const key = String(matcher.keyValue ?? matcher.key);

    if (key === InternalTxConflictFilterValueKeys.FROM_TIMESTAMP) {
      // No serializer of its own: the bounds are stored as the timestamps they are sent as, and the
      // date editor reads and writes them through `formatBound`/`parseBound`.
      result.push(toDateFieldDef({
        formatBound: formatDate,
        key: 'period',
        label: t('internal_tx_conflicts.filter.period'),
        lowerKey: InternalTxConflictFilterValueKeys.FROM_TIMESTAMP,
        parseBound: parseDate,
        upperKey: InternalTxConflictFilterValueKeys.TO_TIMESTAMP,
      }));
      continue;
    }

    // The second bound of the collapsed pair is already represented by the pill above.
    if (key === InternalTxConflictFilterValueKeys.TO_TIMESTAMP)
      continue;

    if (key === InternalTxConflictFilterValueKeys.CHAIN) {
      result.push({
        ...decorateSharedField(toFieldDef(matcher), SharedFieldKinds.CHAIN, resolvers),
        // The matcher description is a long "filter by …" hint; the pill says what the column says.
        label: t('internal_tx_conflicts.columns.chain'),
      });
      continue;
    }

    result.push(toFieldDef(matcher));
  }

  return result;
}
