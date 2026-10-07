import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { HistoricalBalanceRow, HistoricalBalancesSummary } from '@/modules/statistics/historical-balances/historical-balances-view';
import { useAssetInfoRetrieval } from '@/modules/assets/use-asset-info-retrieval';
import { downloadFileByTextContent } from '@/modules/core/common/file/download';
import { useSetting } from '@/modules/settings/use-setting';
import { toDateKey } from '@/modules/statistics/historical-balances/as-of-date';
import { historicalBalancesCsv } from '@/modules/statistics/historical-balances/historical-balances-csv';

interface HistoricalBalancesExportSource {
  rows: MaybeRefOrGetter<HistoricalBalanceRow[]>;
  summary: MaybeRefOrGetter<HistoricalBalancesSummary>;
  /** The as-of time the rows were loaded and priced for, in unix seconds. */
  timestamp: MaybeRefOrGetter<number>;
  loading: MaybeRefOrGetter<boolean>;
  processingRequired: MaybeRefOrGetter<boolean>;
  locations: MaybeRefOrGetter<string[]>;
  accounts: MaybeRefOrGetter<string[]>;
  search: MaybeRefOrGetter<string>;
}

interface UseHistoricalBalancesExportReturn {
  /** Why the export is not offered yet; undefined once it is. */
  blockedReason: ComputedRef<string | undefined>;
  exportCsv: () => void;
}

/**
 * Downloads the shown balances as CSV, once they are complete enough to stand for the day.
 *
 * @remarks
 * Blocked while the day is loading, while history events wait to be processed, and while any price is
 * still loading, since each of those would leave a figure in the file that is not the day's.
 */
export function useHistoricalBalancesExport(source: HistoricalBalancesExportSource): UseHistoricalBalancesExportReturn {
  const { t } = useI18n({ useScope: 'global' });

  const currency = useSetting('currencySymbol');
  const delimiter = useSetting('csvExportDelimiter');
  const { getAssetField } = useAssetInfoRetrieval();

  const blockedReason = computed<string | undefined>(() => {
    if (toValue(source.loading))
      return t('historical_balances.export.blocked.loading');
    if (toValue(source.processingRequired))
      return t('historical_balances.export.blocked.processing');
    if (toValue(source.summary).pendingCount > 0)
      return t('historical_balances.export.blocked.pending');
    if (toValue(source.rows).length === 0)
      return t('historical_balances.export.blocked.empty');
    return undefined;
  });

  function describeFilter(): string {
    const parts: [string, string[]][] = [
      ['location', toValue(source.locations)],
      ['account', toValue(source.accounts)],
      ['asset', [toValue(source.search).trim()].filter(Boolean)],
    ];
    return parts
      .filter(([, values]) => values.length > 0)
      .map(([name, values]) => `${name}: ${values.join(', ')}`)
      .join('; ');
  }

  function exportCsv(): void {
    const timestamp = toValue(source.timestamp);
    const csv = historicalBalancesCsv({
      currency: get(currency),
      delimiter: get(delimiter) || ',',
      filter: describeFilter(),
      rows: toValue(source.rows),
      symbolOf: asset => getAssetField(asset, 'symbol'),
      timestamp,
      timezone: new Intl.DateTimeFormat().resolvedOptions().timeZone,
      total: toValue(source.summary).total,
    });
    downloadFileByTextContent(csv, `historical-balances-${toDateKey(timestamp)}.csv`, 'text/csv');
  }

  return { blockedReason, exportCsv };
}
