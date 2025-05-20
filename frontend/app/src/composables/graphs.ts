import type { Ref } from 'vue';
import { useDarkMode } from '@/composables/dark-mode';
import { type BigNumber, type GraphApi, Zero } from '@rotki/common';
import { LineChart, PieChart } from 'echarts/charts';
import { DataZoomComponent, GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { THEME_KEY } from 'vue-echarts';

export function initGraph(): void {
  use([
    CanvasRenderer,
    LineChart,
    TooltipComponent,
    GridComponent,
    DataZoomComponent,
    PieChart,
    LegendComponent,
  ]);
}

export function useGraph(): GraphApi {
  const { isDark } = useRotkiTheme();

  const { store } = useRotkiTheme();

  provide(THEME_KEY, store);

  const { usedTheme } = useDarkMode();

  const white = '#ffffff';
  const secondaryBlack = '#3f1300';

  const baseColor = computed(() => get(usedTheme).graph);

  const gradient = computed(() => {
    const color = get(baseColor);
    return {
      color: {
        colorStops: [
          { color: `${color}80`, offset: 0 },
          { color: `${color}00`, offset: 1 },
        ],
        type: 'linear',
        x: 0,
        x2: 0,
        y: 0,
        y2: 1,
      },
    };
  });

  const secondaryColor = computed(() => (get(isDark) ? white : secondaryBlack));

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
