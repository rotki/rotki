import type { NetValue } from '@rotki/common';
import type { EChartsOption, LineSeriesOption, XAXisComponentOption, YAXisComponentOption } from 'echarts';
import type { DataZoomComponentOption, GridComponentOption } from 'echarts/components';
import type { ComputedRef, Ref } from 'vue';
import { useNewGraph } from '@/composables/graphs';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

interface AxisConfig {
  xAxis: XAXisComponentOption;
  yAxis: YAXisComponentOption;
}

export interface UseNetValueChartConfigReturn {
  chartOption: ComputedRef<EChartsOption>;
}

export function useNetValueChartConfig(chartData: Ref<NetValue>): UseNetValueChartConfigReturn {
  const data = computed<number[][]>(() => {
    const { data, times } = get(chartData);
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
  const { baseColor, gradient } = useNewGraph();

  const createSliderZoomOptions = (): DataZoomComponentOption => ({
    handleSize: 20,
    height: 30,
    rangeMode: ['value', 'value'],
    realtime: true,
    show: true,
    showDetail: false,
    type: 'slider',
    zoomOnMouseWheel: false,
  });

  const createInsideDataZoom = (): DataZoomComponentOption => ({
    rangeMode: ['value', 'value'],
    showDetail: false,
    type: 'inside',
  });

  const createDataZoomConfig = (): DataZoomComponentOption[] => {
    const dataZoomOptions: DataZoomComponentOption[] = [createInsideDataZoom()];

    if (get(showGraphRangeSelector)) {
      dataZoomOptions.unshift(createSliderZoomOptions());
    }

    return dataZoomOptions;
  };

  const createGridConfig = (): GridComponentOption => ({
    bottom: get(showGraphRangeSelector) ? 56 : 16,
    containLabel: true,
    left: 16,
    right: 16,
    top: 16,
  });

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

  const chartOption = computed<EChartsOption>(() => ({
    backgroundColor: 'transparent',
    dataZoom: createDataZoomConfig(),
    grid: createGridConfig(),
    series: createSeriesConfig(),
    tooltip: {
      trigger: 'axis',
    },
    ...createAxisConfig(),
  }));

  return {
    chartOption,
  };
}
