import type { Ref } from 'vue';
import { useDarkMode } from '@/composables/dark-mode';
import { assert, type BigNumber, type GraphApi, type NewGraphApi, Zero } from '@rotki/common';
import { Chart, registerables } from 'chart.js';
import zoomPlugin from 'chartjs-plugin-zoom';
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

  // chart.js
  Chart.defaults.font.family = 'Roboto';
  Chart.register(...registerables);
  Chart.register(zoomPlugin);
}

export function useNewGraph(): NewGraphApi {
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

export function useGraph(canvasId: string): GraphApi {
  const getCanvasCtx = (): CanvasRenderingContext2D => {
    const canvas = document.getElementById(canvasId);
    assert(canvas && canvas instanceof HTMLCanvasElement, 'Canvas could not be found');
    const context = canvas.getContext('2d');
    assert(context, 'Context could not be found');
    return context;
  };

  const { isDark } = useRotkiTheme();

  const { usedTheme } = useDarkMode();

  const white = '#ffffff';
  const secondaryBlack = '#3f1300';

  const baseColor = computed(() => get(usedTheme).graph);
  const fadeColor = computed(() => (get(isDark) ? '#1e1e1e' : white));

  const gradient = computed(() => {
    const context = getCanvasCtx();
    const areaGradient = context.createLinearGradient(0, 0, 0, context.canvas.height * 0.5 || 300);
    areaGradient.addColorStop(0, get(baseColor));
    areaGradient.addColorStop(1, `${get(fadeColor)}00`);
    return areaGradient;
  });

  const secondaryColor = computed(() => (get(isDark) ? white : secondaryBlack));
  const backgroundColor = computed(() => (!get(isDark) ? white : secondaryBlack));

  const fontColor = computed(() => (get(isDark) ? 'rgba(255,255,255,.5)' : 'rgba(0,0,0,.7)'));
  const gridColor = computed(() => (get(isDark) ? '#555' : '#ddd'));

  return {
    backgroundColor,
    baseColor,
    fontColor,
    getCanvasCtx,
    gradient,
    gridColor,
    secondaryColor,
  };
}
