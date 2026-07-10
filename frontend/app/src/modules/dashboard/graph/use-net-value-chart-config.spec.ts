import type { DataZoomComponentOption } from 'echarts/components';
import type { NetValueChartData } from '@/modules/dashboard/graph/types';
import { bigNumberify } from '@rotki/common';
import { get } from '@vueuse/core';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useNetValueChartConfig } from '@/modules/dashboard/graph/use-net-value-chart-config';

const state = vi.hoisted((): { graphZeroBased: boolean; showGraphRangeSelector: boolean; baseColor: string } => ({
  baseColor: '#123456',
  graphZeroBased: false,
  showGraphRangeSelector: false,
}));

vi.mock('@/modules/settings/use-setting', async (): Promise<{ useSetting: (key: string) => unknown }> => {
  const { computed } = await import('vue');
  return {
    useSetting: (key: string): unknown =>
      computed(() => (key === 'graphZeroBased' ? state.graphZeroBased : state.showGraphRangeSelector)),
  };
});

vi.mock('@/modules/statistics/use-graph', async (): Promise<{ useGraph: () => unknown }> => {
  const { computed } = await import('vue');
  return {
    useGraph: (): unknown => ({
      baseColor: computed(() => state.baseColor),
      gradient: computed(() => ({ color: state.baseColor })),
    }),
  };
});

function chartData(overrides?: Partial<NetValueChartData>): NetValueChartData {
  return { data: [bigNumberify(10), bigNumberify(20)], snapshotCount: 2, times: [1, 2], ...overrides };
}

function seriesData(option: ReturnType<typeof useNetValueChartConfig>): unknown {
  const series = get(option.chartOption).series;
  const first = Array.isArray(series) ? series[0] : series;
  return first && 'data' in first ? first.data : undefined;
}

function dataZoom(option: ReturnType<typeof useNetValueChartConfig>): DataZoomComponentOption[] {
  const zoom = get(option.chartOption).dataZoom;
  if (Array.isArray(zoom))
    return zoom;
  return zoom ? [zoom] : [];
}

describe('useNetValueChartConfig', () => {
  beforeEach(() => {
    state.graphZeroBased = false;
    state.showGraphRangeSelector = false;
    state.baseColor = '#123456';
  });

  it('should map times and values into millisecond data points', () => {
    const option = useNetValueChartConfig(() => chartData());
    expect(seriesData(option)).toEqual([[1000, 10], [2000, 20]]);
  });

  it('should return an empty series when there is no data', () => {
    const option = useNetValueChartConfig(() => chartData({ data: [], times: [] }));
    expect(seriesData(option)).toEqual([]);
  });

  it('should include only the inside zoom when the range selector is hidden', () => {
    const option = useNetValueChartConfig(() => chartData());
    const zooms = dataZoom(option);
    expect(zooms).toHaveLength(1);
    expect(zooms[0].type).toBe('inside');
    expect(get(option.chartOption).grid).toMatchObject({ bottom: 16 });
  });

  it('should prepend the slider zoom when the range selector is shown', () => {
    state.showGraphRangeSelector = true;
    const option = useNetValueChartConfig(() => chartData());
    const zooms = dataZoom(option);
    expect(zooms).toHaveLength(2);
    expect(zooms[0].type).toBe('slider');
    expect(zooms[1].type).toBe('inside');
    expect(get(option.chartOption).grid).toMatchObject({ bottom: 56 });
  });

  it('should persist the active zoom bounds from the range in seconds', () => {
    const option = useNetValueChartConfig(() => chartData(), () => ({ end: 20, start: 10 }));
    const zooms = dataZoom(option);
    expect(zooms[0].startValue).toBe(10000);
    expect(zooms[0].endValue).toBe(20000);
  });

  it('should omit zoom bounds when there is no active range', () => {
    const option = useNetValueChartConfig(() => chartData());
    const zooms = dataZoom(option);
    expect(zooms[0].startValue).toBeUndefined();
    expect(zooms[0].endValue).toBeUndefined();
  });

  it('should style the series with the graph colors', () => {
    state.baseColor = '#abcdef';
    const option = useNetValueChartConfig(() => chartData());
    const series = get(option.chartOption).series;
    const first = Array.isArray(series) ? series[0] : series;
    expect(first).toMatchObject({
      areaStyle: { color: '#abcdef' },
      itemStyle: { color: '#abcdef' },
      lineStyle: { color: '#abcdef' },
    });
  });

  describe('y axis min/max', () => {
    function yAxisMin(zeroBased: boolean): (value: { min: number; max: number }) => unknown {
      state.graphZeroBased = zeroBased;
      const option = useNetValueChartConfig(() => chartData());
      const yAxis = get(option.chartOption).yAxis;
      const axis = Array.isArray(yAxis) ? yAxis[0] : yAxis;
      const min = axis?.min;
      if (typeof min !== 'function')
        throw new TypeError('expected a function min');
      return min;
    }

    it('should clamp to zero when graphZeroBased is enabled', () => {
      expect(yAxisMin(true)({ max: 100, min: 40 })).toBe(0);
    });

    it('should return zero when the minimum is already zero', () => {
      expect(yAxisMin(false)({ max: 100, min: 0 })).toBe(0);
    });

    it('should pad below the minimum when not zero based', () => {
      expect(yAxisMin(false)({ max: 100, min: 40 })).toBe(40 - (100 - 40) * 0.1);
    });
  });
});
