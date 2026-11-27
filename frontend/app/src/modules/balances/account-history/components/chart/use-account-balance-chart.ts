import type { EChartsOption, LineSeriesOption } from 'echarts';
import { get } from '@vueuse/shared';
import { computed, type ComputedRef, type MaybeRefOrGetter, toValue } from 'vue';
import { alignBuckets, type BalancePoint, type BucketSeries } from '@/modules/balances/account-history/balance-series';
import { TIME_AXIS_LABEL } from '@/modules/dashboard/graph/use-net-value-chart-config';
import { useGraph } from '@/modules/statistics/use-graph';

export const BalanceChartMode = {
  /** One area per bucket, stacked, so the top edge is the account's whole balance. */
  STACKED: 'stacked',
  /** The buckets added up into one line. */
  TOTAL: 'total',
} as const;

export type BalanceChartMode = typeof BalanceChartMode[keyof typeof BalanceChartMode];

interface AccountBalanceChartOptions {
  buckets: MaybeRefOrGetter<readonly BucketSeries[]>;
  total: MaybeRefOrGetter<readonly BalancePoint[]>;
  mode: MaybeRefOrGetter<BalanceChartMode>;
  /** Names a bucket in the legend and tooltip. */
  bucketLabel: (bucket: BucketSeries) => string;
  /** False in privacy mode: the axis and tooltip then leave the amounts out. */
  showAmounts: MaybeRefOrGetter<boolean>;
}

interface UseAccountBalanceChartReturn {
  option: ComputedRef<EChartsOption>;
}

const MS = 1000;

function formatAmount(value: unknown): string {
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 8 });
}

/**
 * The account balance chart's ECharts options.
 *
 * @remarks
 * Balances change only at events, so every line is drawn as steps (`step: 'end'`) rather than
 * interpolated between events, which would show balances the account never held. The stacked mode
 * aligns the buckets first, since ECharts adds stacked values up by position.
 */
export function useAccountBalanceChart(options: AccountBalanceChartOptions): UseAccountBalanceChartReturn {
  const { bucketLabel, buckets, mode, showAmounts, total } = options;
  const { baseColor, gradient } = useGraph();

  const stackedSeries = computed<LineSeriesOption[]>(() => {
    const list = toValue(buckets);
    const { rows, times } = alignBuckets(list);
    return list.map((bucket, index) => ({
      areaStyle: { opacity: 0.3 },
      data: times.map((time, position) => [time * MS, rows[index]?.[position]?.toNumber() ?? 0]),
      lineStyle: { width: 1.5 },
      name: bucketLabel(bucket),
      showSymbol: false,
      stack: 'balance',
      step: 'end',
      type: 'line',
    }));
  });

  const totalSeries = computed<LineSeriesOption[]>(() => [{
    areaStyle: get(gradient),
    data: toValue(total).map(point => [point.time * MS, point.value.toNumber()]),
    itemStyle: { color: get(baseColor) },
    lineStyle: { color: get(baseColor), width: 1.5 },
    showSymbol: false,
    step: 'end',
    type: 'line',
  }]);

  const option = computed<EChartsOption>(() => {
    const stacked = toValue(mode) === BalanceChartMode.STACKED;
    const series = stacked ? get(stackedSeries) : get(totalSeries);
    const amounts = toValue(showAmounts);
    return {
      backgroundColor: 'transparent',
      grid: { bottom: 24, containLabel: true, left: 8, right: 16, top: stacked ? 36 : 12 },
      legend: { show: stacked && series.length > 1, top: 0, type: 'scroll' },
      series,
      tooltip: {
        trigger: 'axis',
        valueFormatter: (value): string => (amounts ? formatAmount(value) : '***'),
      },
      xAxis: { axisLabel: TIME_AXIS_LABEL, type: 'time' },
      yAxis: {
        axisLabel: { formatter: (value: number): string => (amounts ? formatAmount(value) : '') },
        type: 'value',
      },
    };
  });

  return { option };
}
