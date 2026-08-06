import type { SharedFieldResolvers } from '@/modules/core/table/filters/shared/use-shared-field-resolvers';
import type { FieldDef } from '@/modules/core/table/pill/core/types';
import { type Matcher, OraclePriceFilterValueKeys } from '@/modules/assets/prices/use-oracle-prices-filter';
import { decorateSharedField, type SharedFieldKind, SharedFieldKinds } from '@/modules/core/table/filters/shared/shared-fields';
import { toDateFieldDef, toFieldDef } from '@/modules/core/table/pill/core/field-adapter';

type Translate = (key: string) => string;

/**
 * Short, noun-style pill labels. The matcher `description` is a long "filter by …" hint that reads
 * badly on a pill, so each field gets a concise label keyed by its wire key.
 */
function shortLabels(t: Translate): Record<string, string> {
  return {
    [OraclePriceFilterValueKeys.FROM_ASSET]: t('oracle_prices.filter_field_labels.from_asset'),
    [OraclePriceFilterValueKeys.SOURCE]: t('oracle_prices.filter_field_labels.source'),
    [OraclePriceFilterValueKeys.TO_ASSET]: t('oracle_prices.filter_field_labels.to_asset'),
  };
}

// Both asset fields are the shared asset pill, so an asset looks the same here as it does in the
// history bar. The source is this table's own enum and has nothing to share.
const sharedKinds: Partial<Record<string, SharedFieldKind>> = {
  [OraclePriceFilterValueKeys.FROM_ASSET]: SharedFieldKinds.ASSET,
  [OraclePriceFilterValueKeys.TO_ASSET]: SharedFieldKinds.ASSET,
};

/**
 * The pill-bar fields for the oracle prices table: the asset and source matchers, plus the two
 * date matchers folded into one `period` pill with a from/to editor, the way history's period pill
 * works. The wire form is unchanged — the bounds still serialize to `fromTimestamp`/`toTimestamp`.
 */
export function toOraclePriceFields(
  matchers: Matcher[],
  resolvers: SharedFieldResolvers,
  t: Translate,
  resolveSourceLabel: (value: string) => string,
): FieldDef[] {
  const { formatDate, parseDate } = resolvers;
  const labels = shortLabels(t);
  const result: FieldDef[] = [];

  for (const matcher of matchers) {
    const key = String(matcher.keyValue ?? matcher.key);

    if (key === OraclePriceFilterValueKeys.START) {
      // No serializer of its own: the two bounds are stored as the timestamps they are sent as, and
      // the date editor reads and writes them through `formatBound`/`parseBound`. The matchers'
      // own date serializers belong to the old bar, where the user typed a formatted date.
      result.push(toDateFieldDef({
        formatBound: formatDate,
        key: 'period',
        label: t('oracle_prices.filter_field_labels.period'),
        lowerKey: OraclePriceFilterValueKeys.START,
        parseBound: parseDate,
        upperKey: OraclePriceFilterValueKeys.END,
      }));
      continue;
    }

    // The second bound of the collapsed pair is already represented by the pill above.
    if (key === OraclePriceFilterValueKeys.END)
      continue;

    const field = decorateSharedField(toFieldDef(matcher), sharedKinds[key], resolvers);
    result.push({
      ...field,
      ...(labels[key] ? { label: labels[key] } : {}),
      // A raw oracle id (`cryptocompare`) is not what the table calls it, and the pill has to read
      // the same as the source chip in the row it filters to.
      ...(key === OraclePriceFilterValueKeys.SOURCE ? { resolveLabel: resolveSourceLabel } : {}),
    });
  }

  return result;
}
