import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { SparklinePoint } from '@/modules/history/balances/use-accounting-overlay';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { type BigNumber, Zero } from '@rotki/common';
import { isErr } from 'plainfp/result';
import { useAmountDisplaySettings } from '@/modules/assets/amount-display';
import { useHistoricalBalancesApi } from '@/modules/balances/api/use-historical-balances-api';
import { mergeSameScopeBuckets, valueAt } from '@/modules/history/balances/accounting-overlay-helpers';
import { downsample, SPARKLINE_MAX_POINTS } from '@/modules/history/balances/sparkline';
import { HistoricalBalanceSeriesResponse } from '@/modules/history/balances/types';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { ActivityKind, ActivityPart, makeActivityId, useNativeTask } from '@/modules/task-center/use-native-task';

/** Load a breakdown chart only while open and visible, keeping its endpoint at the exact snapshot. */
export function useAccountingOverlaySparkline(
  event: MaybeRefOrGetter<HistoryEventEntry>,
  open: MaybeRefOrGetter<boolean>,
  balance: MaybeRefOrGetter<BigNumber | undefined>,
): ComputedRef<SparklinePoint[]> {
  const { t } = useI18n({ useScope: 'global' });
  const { allowed } = useFeatureAccess(PremiumFeature.GRAPHS_VIEW);
  const { shouldShowAmount } = useAmountDisplaySettings();
  const { fetchHistoricalBalanceSeries } = useHistoricalBalancesApi();
  const { submitTask } = useNativeTask();
  const points = shallowRef<SparklinePoint[]>([]);
  let cachedKey: string | undefined;

  const queryKey = computed<string | undefined>(() => {
    const entry = toValue(event);
    const total = toValue(balance);
    if (!toValue(open) || !get(allowed) || !get(shouldShowAmount) || !entry.locationLabel || total === undefined)
      return undefined;
    return JSON.stringify([entry.identifier, entry.locationLabel, entry.asset, entry.timestamp, total.toString()]);
  });

  async function load(key: string | undefined): Promise<void> {
    if (!key || key === cachedKey)
      return;
    let stale = false;
    onWatcherCleanup(() => {
      stale = true;
    });
    cachedKey = undefined;
    set(points, []);
    const entry = toValue(event);
    const total = toValue(balance);
    const locationLabel = entry.locationLabel;
    if (!locationLabel || total === undefined)
      return;
    const end = Math.floor(entry.timestamp / 1000);
    try {
      const outcome = await submitTask<HistoricalBalanceSeriesResponse>({
        id: makeActivityId(ActivityKind.HISTORICAL_BALANCES, ActivityPart.SERIES, key),
        kind: ActivityKind.HISTORICAL_BALANCES,
        rerunnable: false,
        title: t('task_center.group.historical_balances'),
        run: async ({ runTask }) => runTask<HistoricalBalanceSeriesResponse>(async () => fetchHistoricalBalanceSeries({
          asset: entry.asset,
          locationLabel,
          toTimestamp: end,
        })),
      });
      if (stale || isErr(outcome))
        return;
      const response = HistoricalBalanceSeriesResponse.parse(outcome.value);
      const buckets = mergeSameScopeBuckets(response.entries.map(bucket => ({
        location: bucket.location,
        protocol: bucket.protocol ?? null,
        times: bucket.times,
        values: bucket.values,
      })));
      const times = [...new Set(buckets.flatMap(bucket => bucket.times).filter(time => time < end))].sort((a, b) => a - b);
      const sampled = downsample([...times, end], SPARKLINE_MAX_POINTS);
      set(points, sampled.map(time => ({
        time,
        value: time === end ? total.toNumber() : buckets.reduce((sum, bucket) => sum.plus(valueAt(bucket, time)), Zero).toNumber(),
      })));
      cachedKey = key;
    }
    catch {
      if (!stale)
        set(points, []);
    }
  }

  watch(queryKey, load, { immediate: true });
  return computed<SparklinePoint[]>(() => get(points));
}
