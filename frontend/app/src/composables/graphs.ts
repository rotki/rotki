import type { Ref } from 'vue';
import { type BigNumber, type GradientArea, type NewGraphApi, Zero } from '@rotki/common';
import { LineChart, PieChart } from 'echarts/charts';
import {
  BrushComponent,
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  ToolboxComponent,
  TooltipComponent,
} from 'echarts/components';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { THEME_KEY } from 'vue-echarts';
import { useDarkMode } from '@/composables/dark-mode';

export function initGraph(): void {
  use([
    CanvasRenderer,
    LineChart,
    TooltipComponent,
    GridComponent,
    DataZoomComponent,
    PieChart,
    LegendComponent,
    BrushComponent,
    ToolboxComponent,
  ]);
}

export function useGraph(): NewGraphApi {
  const { isDark } = useRotkiTheme();
  const { store } = useRotkiTheme();
  const { usedTheme } = useDarkMode();

  provide(THEME_KEY, store);

  const white = '#ffffff';
  const secondaryBlack = '#3f1300';

  const baseColor = computed<string>(() => get(usedTheme).graph);

  const gradient = computed<GradientArea>(() => {
    const color = get(baseColor);
    const colorStops = [
      { color: `${color}80`, offset: 0 },
      { color: `${color}00`, offset: 1 },
    ];
    return {
      color: {
        colorStops,
        type: 'linear',
        x: 0,
        x2: 0,
        y: 0,
        y2: 1,
      },
    };
  });

  const secondaryColor = computed<string>(() => (get(isDark) ? white : secondaryBlack));

  return {
    baseColor,
    gradient,
    secondaryColor,
  };
}

export interface TooltipData {
  visible: boolean;
  x: number;
  y: number;
  timestamp: number;
  value: BigNumber;
  currentBalance: boolean;
}

interface UseGraphTooltipReturn {
  tooltipData: Ref<TooltipData>;
  resetTooltipData: () => void;
}

export function useGraphTooltip(): UseGraphTooltipReturn {
  const defaultTooltipData = (): TooltipData => ({
    currentBalance: false,
    timestamp: 0,
    value: Zero,
    visible: false,
    x: 0,
    y: 0,
  });

  const tooltipData = ref<TooltipData>(defaultTooltipData());

  function resetTooltipData(): void {
    set(tooltipData, {
      ...get(tooltipData),
      visible: false,
    });
  }

  return {
    resetTooltipData,
    tooltipData,
  };
}
