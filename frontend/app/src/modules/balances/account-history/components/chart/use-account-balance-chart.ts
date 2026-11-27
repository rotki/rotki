import type { EChartsOption, LineSeriesOption, TooltipComponentFormatterCallbackParams } from 'echarts';
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
  /** The asset's symbol, written after each amount in the tooltip. */
  unit: MaybeRefOrGetter<string>;
  /** Formats a point's time, unix milliseconds, the way the user reads dates. */
  formatTime: (milliseconds: number) => string;
}

interface UseAccountBalanceChartReturn {
  option: ComputedRef<EChartsOption>;
}

const MS = 1000;

function formatAmount(value: unknown): string {
  return Number(value).toLocaleString(undefined, { maximumFractionDigits: 8 });
}

function escapeHtml(text: string): string {
  return text.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;');
}

/** The point a tooltip row stands for: the series' marker and name, and its `[ms, amount]` value. */
interface TooltipRow {
  readonly marker?: unknown;
  readonly seriesName?: string;
  readonly value?: unknown;
}

function rowsOf(params: TooltipComponentFormatterCallbackParams): TooltipRow[] {
  return Array.isArray(params) ? params : [params];
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
  const { bucketLabel, buckets, formatTime, mode, showAmounts, total, unit } = options;
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
        formatter: (params: TooltipComponentFormatterCallbackParams): string => {
          const rows = rowsOf(params);
          const first = rows[0]?.value;
          const time = Array.isArray(first) ? Number(first[0]) : Number.NaN;
          const symbol = escapeHtml(toValue(unit));
          const lines = rows.map((row) => {
            const amount = Array.isArray(row.value) ? row.value[1] : row.value;
            const shown = amounts ? `${formatAmount(amount)} ${symbol}` : '***';
            const name = row.seriesName ? `${escapeHtml(row.seriesName)} ` : '';
            return `${String(row.marker ?? '')}${name}<b>${shown}</b>`;
          });
          return [Number.isNaN(time) ? '' : escapeHtml(formatTime(time)), ...lines].filter(Boolean).join('<br/>');
        },
        trigger: 'axis',
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
