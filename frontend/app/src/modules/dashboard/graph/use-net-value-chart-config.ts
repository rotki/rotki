import type {
  BrushComponentOption,
  EChartsOption,
  LineSeriesOption,
  ToolboxComponentOption,
  XAXisComponentOption,
  YAXisComponentOption,
} from 'echarts';
import type { DataZoomComponentOption, GridComponentOption } from 'echarts/components';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import type { NetValueZoomRange } from '@/modules/dashboard/graph/net-value-stats';
import type { NetValueChartData } from '@/modules/dashboard/graph/types';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useGraph } from '@/modules/statistics/use-graph';

interface AxisConfig {
  xAxis: XAXisComponentOption;
  yAxis: YAXisComponentOption;
}

interface UseNetValueChartConfigReturn {
  chartOption: ComputedRef<EChartsOption>;
}

export function useNetValueChartConfig(
  chartData: MaybeRefOrGetter<NetValueChartData>,
  zoomRange: MaybeRefOrGetter<NetValueZoomRange | undefined> = () => undefined,
): UseNetValueChartConfigReturn {
  const data = computed<number[][]>(() => {
    const { data, times } = toValue(chartData);
    if (!(times?.length && data?.length)) {
      return [];
    }
    const MILLISECONDS = 1000;
    return times.map((epoch, index) => [
      epoch * MILLISECONDS,
      Number(data[index]),
    ]);
  });

  const { graphZeroBased, showGraphRangeSelector } = storeToRefs(useFrontendSettingsStore());
  const { baseColor, gradient } = useGraph();

  const MS = 1000;

  // Persist the active zoom across chart rebuilds (chartData refreshes every
  // balance update). Without this, dataZoom rebuilds with no start/end and
  // ECharts snaps the slider back to full range.
  const zoomBounds = computed<{ startValue?: number; endValue?: number }>(() => {
    const range = toValue(zoomRange);
    if (!range)
      return {};
    return { endValue: range.end * MS, startValue: range.start * MS };
  });

  const createSliderZoomOptions = (): DataZoomComponentOption => ({
    handleSize: 20,
    height: 30,
    rangeMode: ['value', 'value'],
    realtime: true,
    show: true,
    showDetail: false,
    type: 'slider',
    zoomOnMouseWheel: true,
    ...get(zoomBounds),
  });

  const createInsideDataZoom = (): DataZoomComponentOption => ({
    moveOnMouseMove: false,
    moveOnMouseWheel: false,
    preventDefaultMouseMove: false,
    rangeMode: ['value', 'value'],
    showDetail: false,
    type: 'inside',
    zoomOnMouseWheel: true,
    ...get(zoomBounds),
  });

  const createDataZoomConfig = (): DataZoomComponentOption[] => {
    const dataZoomOptions: DataZoomComponentOption[] = [createInsideDataZoom()];

    if (get(showGraphRangeSelector)) {
      dataZoomOptions.unshift(createSliderZoomOptions());
    }

    return dataZoomOptions;
  };

  const createGridConfig = (): GridComponentOption => {
    const bottom = get(showGraphRangeSelector) ? 56 : 16;
    return {
      bottom,
      left: 16,
      outerBounds: {
        bottom,
      },
      right: 16,
      top: 16,
    };
  };

  const createSeriesConfig = (): LineSeriesOption[] => [{
    areaStyle: get(gradient),
    data: get(data),
    itemStyle: { color: get(baseColor) },
    lineStyle: { color: get(baseColor) },
    showSymbol: false,
    smooth: true,
    symbol: 'circle',
    symbolSize: 8,
    type: 'line',
  }];

  const createAxisConfig = (): AxisConfig => ({
    xAxis: {
      axisLabel: { show: true },
      axisLine: { show: false },
      axisTick: { show: false },
      type: 'time',
    },
    yAxis: {
      axisLabel: { show: false },
      max: (value: { min: number; max: number }) =>
        value.max,
      min: (value: { min: number; max: number }): number => {
        if (get(graphZeroBased) || value.min === 0) {
          return 0;
        }

        return value.min - (value.max - value.min) * 0.1;
      },
      splitLine: { show: false },
      type: 'value',
    },
  });

  const createBrushConfig = (): BrushComponentOption => ({
    brushLink: 'all',
    throttleDelay: 300,
    throttleType: 'debounce',
    xAxisIndex: 0,
  });

  const createToolboxConfig = (): ToolboxComponentOption => ({
    feature: {
      dataZoom: {
        yAxisIndex: false,
      },
    },
    top: -100,
  });

  const chartOption = computed<EChartsOption>(() => ({
    backgroundColor: 'transparent',
    brush: createBrushConfig(),
    dataZoom: createDataZoomConfig(),
    grid: createGridConfig(),
    series: createSeriesConfig(),
    toolbox: createToolboxConfig(),
    tooltip: {
      trigger: 'axis',
    },
    ...createAxisConfig(),
  }));

  return {
    chartOption,
  };
}
