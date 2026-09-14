import { isErr } from 'plainfp/result';
import { msg } from '@/message-key';
import { useHistoricalBalancesApi } from '@/modules/balances/api/use-historical-balances-api';
import { logger } from '@/modules/core/common/logging/logging';
import { mergeSameScopeBuckets, type PreparedBucket } from '@/modules/history/balances/accounting-overlay-helpers';
import { HistoricalBalanceSeriesResponse } from '@/modules/history/balances/types';
import { activityLabelFor } from '@/modules/task-center/activity-labels';
import { ActivityKind, ActivityPart, makeActivityId, useNativeTask } from '@/modules/task-center/use-native-task';

export interface UseAccountingOverlaySeriesReturn {
  /** The merged balance series for one account and asset, or undefined when it could not be loaded. */
  seriesFor: (locationLabel: string, asset: string) => Promise<PreparedBucket[] | undefined>;
  /** Drops every loaded series, so the next request refetches. */
  reset: () => void;
}

/**
 * Loads the breakdown chart's balance series once per account and asset.
 *
 * @remarks
 * Every row of one account and asset draws from the same full series, so opening the breakdown on
 * one row after another starts no new task. A series that failed to load is not kept, and the next
 * request retries it.
 */
export function useAccountingOverlaySeries(): UseAccountingOverlaySeriesReturn {
  const { t } = useI18n({ useScope: 'global' });
  const { fetchHistoricalBalanceSeries } = useHistoricalBalancesApi();
  const { submitTask } = useNativeTask();
  let loaded = new Map<string, Promise<PreparedBucket[] | undefined>>();

  async function fetchSeries(locationLabel: string, asset: string): Promise<PreparedBucket[] | undefined> {
    try {
      const outcome = await submitTask<HistoricalBalanceSeriesResponse>({
        id: makeActivityId(ActivityKind.HISTORICAL_BALANCES, ActivityPart.SERIES, locationLabel, asset),
        kind: ActivityKind.HISTORICAL_BALANCES,
        rerunnable: false,
        run: async ({ runTask }) => runTask<HistoricalBalanceSeriesResponse>(async () => fetchHistoricalBalanceSeries({ asset, locationLabel })),
        subtitle: activityLabelFor(msg.$t('task_center.activity.historical_balances.series'), { asset }),
        title: t('task_center.group.historical_balances'),
      });
      if (isErr(outcome))
        return undefined;
      return mergeSameScopeBuckets(HistoricalBalanceSeriesResponse.parse(outcome.value).entries.map(entry => ({
        location: entry.location,
        protocol: entry.protocol ?? null,
        times: entry.times,
        values: entry.values,
      })));
    }
    catch (error: unknown) {
      logger.error(error);
      return undefined;
    }
  }

  async function seriesFor(locationLabel: string, asset: string): Promise<PreparedBucket[] | undefined> {
    const key = `${locationLabel} ${asset}`;
    const owner = loaded;
    const existing = owner.get(key);
    if (existing)
      return existing;

    const pending = fetchSeries(locationLabel, asset);
    owner.set(key, pending);
    const series = await pending;
    if (!series && owner.get(key) === pending)
      owner.delete(key);
    return series;
  }

  function reset(): void {
    loaded = new Map();
  }

  return { reset, seriesFor };
}
