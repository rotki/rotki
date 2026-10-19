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
import { useSetting } from '@/modules/settings/use-setting';
import { useGraph } from '@/modules/statistics/use-graph';

interface AxisConfig {
  xAxis: XAXisComponentOption;
  yAxis: YAXisComponentOption;
}

interface UseNetValueChartConfigReturn {
  chartOption: ComputedRef<EChartsOption>;
}

/**
 * Time axis labels that name their month and never draw over each other.
 *
 * @remarks
 * ECharts adds a bold label at each month and year boundary on top of its regular ticks, so a
 * boundary a day or two from a tick drew both labels in one spot ("Jul" over "3"). A day tick now
 * carries its month and an overlapping label is dropped, so whichever survives still dates itself.
 * The first and last data points are not labelled: their exact time ("10:00") read as noise.
 */
const TIME_AXIS_LABEL = {
  formatter: {
    day: '{MMM} {d}',
    hour: '{HH}:{mm}',
    millisecond: '{HH}:{mm}:{ss}',
    minute: '{HH}:{mm}',
    month: '{MMM}',
    second: '{HH}:{mm}:{ss}',
    year: '{yyyy}',
  },
  hideOverlap: true,
  show: true,
  showMaxLabel: false,
  showMinLabel: false,
} satisfies XAXisComponentOption['axisLabel'];

/**
 * The range slider's handle: a stem marking the edge of the range and an 8×16 pill with two grip
 * lines to grab, in an 8×24 box.
 *
 * @remarks
 * It keeps the shape of the ECharts default, whose pill came out a couple of pixels wide at our
 * slider heights. The stem stops at the pill so it does not cross it, and the stem and grip lines
 * are open subpaths, so the border strokes them and the fill leaves them alone. The premium
 * statistics graphs draw the same slider, so the two stay alike.
 */
const SLIDER_HANDLE_ICON = 'path://M4,0V4M4,20V24M2,4h4a2,2,0,0,1,2,2v12a2,2,0,0,1-2,2h-4a2,2,0,0,1-2-2v-12a2,2,0,0,1,2-2ZM3,9V15M5,9V15';

/** Neutral greys for the handle, so it reads as a control rather than as part of the data. */
const SLIDER_HANDLE_COLORS = {
  dark: { border: '#a1a1aa', fill: '#27272a', hover: '#d4d4d8' },
  light: { border: '#a1a1aa', fill: '#ffffff', hover: '#71717a' },
} as const;

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

  const graphZeroBased = useSetting('graphZeroBased');
  const showGraphRangeSelector = useSetting('showGraphRangeSelector');
  const { baseColor, gradient, secondaryColor } = useGraph();
  const { isDark } = useRotkiTheme();

  const MS = 1000;

  /**
   * The active zoom, carried across chart rebuilds.
   *
   * @remarks
   * `chartData` refreshes on every balance update, and a `dataZoom` rebuilt with no start or end
   * makes ECharts snap the slider back to full range.
   */
  const zoomBounds = computed<{ startValue?: number; endValue?: number }>(() => {
    const range = toValue(zoomRange);
    if (!range)
      return {};
    return { endValue: range.end * MS, startValue: range.start * MS };
  });

  const createSliderZoomOptions = (): DataZoomComponentOption => {
    const base = get(baseColor);
    const secondary = get(secondaryColor);
    const handle = SLIDER_HANDLE_COLORS[get(isDark) ? 'dark' : 'light'];
    return {
      backgroundColor: 'transparent',
      borderColor: 'transparent',
      bottom: 8,
      brushSelect: false,
      dataBackground: {
        areaStyle: { color: secondary, opacity: 0.06 },
        lineStyle: { color: secondary, opacity: 0.25 },
      },
      emphasis: { handleStyle: { borderColor: handle.hover } },
      fillerColor: `${base}1f`,
      handleIcon: SLIDER_HANDLE_ICON,
      handleSize: '100%',
      handleStyle: { borderColor: handle.border, borderWidth: 1, color: handle.fill },
      height: 24,
      moveHandleSize: 0,
      rangeMode: ['value', 'value'],
      realtime: true,
      selectedDataBackground: {
        areaStyle: { color: base, opacity: 0.2 },
        lineStyle: { color: base, opacity: 0.7 },
      },
      show: true,
      showDetail: false,
      type: 'slider',
      zoomOnMouseWheel: true,
      ...get(zoomBounds),
    };
  };

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
    const bottom = get(showGraphRangeSelector) ? 48 : 16;
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
    smooth: false,
    symbol: 'circle',
    symbolSize: 8,
    type: 'line',
  }];

  const createAxisConfig = (): AxisConfig => ({
    xAxis: {
      axisLabel: TIME_AXIS_LABEL,
      axisLine: { show: false },
      axisTick: { show: false },
      type: 'time',
    },
    yAxis: {
      axisLabel: { show: false },
      max: (value: { max: number }) =>
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
      /**
       * The axis trigger is kept for the `updateAxisPointer` event that drives our own
       * `NewGraphTooltipWrapper`; `showContent` suppresses echarts' built-in tooltip element, which
       * would otherwise render on top of it.
       */
      showContent: false,
      trigger: 'axis',
    },
    ...createAxisConfig(),
  }));

  return {
    chartOption,
  };
}
