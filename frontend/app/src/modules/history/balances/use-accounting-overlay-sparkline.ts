import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { SparklinePoint } from '@/modules/history/balances/use-accounting-overlay';
import type { UseAccountingOverlaySeriesReturn } from '@/modules/history/balances/use-accounting-overlay-series';
import type { HistoryEventEntry } from '@/modules/history/events/schemas';
import { type BigNumber, Zero } from '@rotki/common';
import { type PreparedBucket, valueAt } from '@/modules/history/balances/accounting-overlay-helpers';
import { downsample, SPARKLINE_MAX_POINTS } from '@/modules/history/balances/sparkline';

interface AccountingOverlaySparklineOptions {
  /** Whether the chart may load at all: premium graphs are allowed and amounts are visible. */
  enabled: MaybeRefOrGetter<boolean>;
  seriesFor: UseAccountingOverlaySeriesReturn['seriesFor'];
}

interface UseAccountingOverlaySparklineReturn {
  points: ComputedRef<SparklinePoint[]>;
  loading: ComputedRef<boolean>;
}

/**
 * The breakdown chart for one event: its account's balance trajectory, ending on the event's snapshot.
 *
 * @remarks
 * The trajectory comes from the series shared by every row of the account and asset. Its last point
 * is the event's own snapshot total rather than a series lookup, because events sharing a timestamp
 * can hold different balances.
 */
export function useAccountingOverlaySparkline(
  event: MaybeRefOrGetter<HistoryEventEntry>,
  balance: MaybeRefOrGetter<BigNumber | undefined>,
  { enabled, seriesFor }: AccountingOverlaySparklineOptions,
): UseAccountingOverlaySparklineReturn {
  const series = shallowRef<PreparedBucket[]>();
  const loading = shallowRef<boolean>(false);

  const points = computed<SparklinePoint[]>(() => {
    const buckets = get(series);
    const total = toValue(balance);
    if (!buckets || total === undefined)
      return [];

    const end = Math.floor(toValue(event).timestamp / 1000);
    const times = [...new Set(buckets.flatMap(bucket => bucket.times).filter(time => time < end))].sort((a, b) => a - b);
    return downsample([...times, end], SPARKLINE_MAX_POINTS).map(time => ({
      time,
      value: time === end ? total.toNumber() : buckets.reduce((sum, bucket) => sum.plus(valueAt(bucket, time)), Zero).toNumber(),
    }));
  });

  async function loadSeries([isEnabled, locationLabel, asset]: [boolean, string | null | undefined, string]): Promise<void> {
    let stale = false;
    onWatcherCleanup(() => {
      stale = true;
    });
    set(series, undefined);
    set(loading, isEnabled && !!locationLabel);
    if (!isEnabled || !locationLabel)
      return;

    const loaded = await seriesFor(locationLabel, asset);
    if (stale)
      return;
    set(series, loaded);
    set(loading, false);
  }

  watch([
    (): boolean => toValue(enabled),
    (): string | null | undefined => toValue(event).locationLabel,
    (): string => toValue(event).asset,
  ], loadSeries, { immediate: true });

  return { loading: computed<boolean>(() => get(loading)), points };
}
