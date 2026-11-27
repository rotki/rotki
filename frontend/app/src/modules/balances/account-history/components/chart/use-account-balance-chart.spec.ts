import type { LineSeriesOption, TooltipComponentFormatterCallbackParams } from 'echarts';
import type { BalancePoint, BucketSeries } from '@/modules/balances/account-history/balance-series';
import { bigNumberify } from '@rotki/common';
import { createMock } from '@test/utils/create-mock';
import { get } from '@vueuse/shared';
import { afterEach, assert, beforeEach, describe, expect, it, vi } from 'vitest';
import { type EffectScope, effectScope, ref } from 'vue';
import { BalanceChartMode, useAccountBalanceChart } from './use-account-balance-chart';

vi.mock('@/modules/statistics/use-graph', async () => {
  const { computed } = await import('vue');
  return {
    useGraph: (): Record<string, unknown> => ({
      baseColor: computed(() => '#000000'),
      gradient: computed(() => ({})),
      secondaryColor: computed(() => '#ffffff'),
    }),
  };
});

function bucket(protocol: string | undefined, values: [number, number][]): BucketSeries {
  return {
    key: `ethereum:${protocol ?? ''}`,
    location: 'ethereum',
    points: values.map(([time, value]) => ({ time, value: bigNumberify(value) })),
    protocol,
  };
}

const buckets = [bucket(undefined, [[100, 1], [300, 2]]), bucket('aave', [[200, 5]])];
const total: BalancePoint[] = [
  { time: 100, value: bigNumberify(1) },
  { time: 200, value: bigNumberify(6) },
  { time: 300, value: bigNumberify(7) },
];

let scope: EffectScope;

function seriesOf(mode: BalanceChartMode, showAmounts = true): { series: LineSeriesOption[]; option: ReturnType<typeof useAccountBalanceChart>['option'] } {
  const result = scope.run(() => useAccountBalanceChart({
    bucketLabel: ({ protocol }) => protocol ?? 'wallet',
    buckets,
    formatTime: (milliseconds: number): string => `day ${milliseconds}`,
    mode: ref<BalanceChartMode>(mode),
    showAmounts,
    total,
    unit: 'ETH',
  }));
  assert(result);
  const { series } = get(result.option);
  assert(Array.isArray(series));
  return { option: result.option, series: series.filter((item): item is LineSeriesOption => item.type === 'line') };
}

function tooltipFor(showAmounts: boolean): string {
  const { option } = seriesOf(BalanceChartMode.STACKED, showAmounts);
  const { tooltip } = get(option);
  assert(tooltip && !Array.isArray(tooltip) && typeof tooltip.formatter === 'function');
  const row = { marker: '<i></i>', seriesName: 'wallet', value: [100_000, 12.5] };
  return String(tooltip.formatter(createMock<TooltipComponentFormatterCallbackParams>(row), ''));
}

describe('useAccountBalanceChart', () => {
  beforeEach(() => {
    scope = effectScope();
  });

  afterEach(() => scope.stop());

  it('should stack one step area per bucket on shared times, in milliseconds', () => {
    const { series } = seriesOf(BalanceChartMode.STACKED);

    expect(series.map(({ name, stack, step }) => ({ name, stack, step }))).toEqual([
      { name: 'wallet', stack: 'balance', step: 'end' },
      { name: 'aave', stack: 'balance', step: 'end' },
    ]);
    expect(series[1]?.data).toEqual([[100_000, 0], [200_000, 5], [300_000, 5]]);
  });

  it('should draw one unstacked step line for the total', () => {
    const { series } = seriesOf(BalanceChartMode.TOTAL);

    expect(series).toHaveLength(1);
    expect(series[0]?.stack).toBeUndefined();
    expect(series[0]?.step).toBe('end');
    expect(series[0]?.data).toEqual([[100_000, 1], [200_000, 6], [300_000, 7]]);
  });

  it('should show a legend only for more than one stacked bucket', () => {
    expect(get(seriesOf(BalanceChartMode.STACKED).option).legend).toMatchObject({ show: true });
    expect(get(seriesOf(BalanceChartMode.TOTAL).option).legend).toMatchObject({ show: false });
  });

  it('should date the tooltip the user\'s way and name the asset after each amount', () => {
    expect(tooltipFor(true)).toBe('day 100000<br/><i></i>wallet <b>12.5 ETH</b>');
  });

  it('should leave amounts out of the tooltip in privacy mode', () => {
    expect(tooltipFor(false)).toBe('day 100000<br/><i></i>wallet <b>***</b>');
  });
});
