import { Chart, type TooltipModel, registerables } from 'chart.js';
import zoomPlugin from 'chartjs-plugin-zoom';
import type { BigNumber, TooltipDisplayOption } from '@rotki/common';

export function initGraph(): void {
  Chart.defaults.font.family = 'Roboto';
  Chart.register(...registerables);
  Chart.register(zoomPlugin);
}

interface UseGraphReturn {
  getCanvasCtx: () => CanvasRenderingContext2D;
  baseColor: ComputedRef<string>;
  gradient: ComputedRef<CanvasGradient>;
  secondaryColor: ComputedRef<string>;
  backgroundColor: ComputedRef<string>;
  fontColor: ComputedRef<string>;
  gridColor: ComputedRef<string>;
}

export function useGraph(canvasId: string): UseGraphReturn {
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

  const fontColor = computed(() => (get(isDark) ? white : 'rgba(0,0,0,.8)'));
  const gridColor = computed(() => (get(isDark) ? '#555' : '#ddd'));

  return {
    getCanvasCtx,
    baseColor,
    gradient,
    secondaryColor,
    backgroundColor,
    fontColor,
    gridColor,
  };
}

export interface TooltipContent {
  readonly time: string;
  readonly value: BigNumber;
  readonly currentBalance?: boolean;
}

interface UseTooltipReturn {
  tooltipDisplayOption: Ref<TooltipDisplayOption>;
  tooltipContent: Ref<TooltipContent>;
  calculateTooltipPosition: (element: HTMLElement, tooltipModel: TooltipModel<'line'>) => Partial<TooltipDisplayOption>;
}

export function useTooltip(id: string): UseTooltipReturn {
  const getDefaultTooltipDisplayOption = (): TooltipDisplayOption => ({
    visible: false,
    left: 0,
    top: 0,
    xAlign: 'left',
    yAlign: 'center',
    id,
  });

  const getDefaultTooltipContent = (): TooltipContent => ({
    time: '',
    value: bigNumberify(0),
  });

  const tooltipDisplayOption = ref<TooltipDisplayOption>(getDefaultTooltipDisplayOption());
  const tooltipContent = ref<TooltipContent>(getDefaultTooltipContent());

  const calculateTooltipPosition = (
    element: HTMLElement,
    tooltipModel: TooltipModel<'line'>,
  ): Partial<TooltipDisplayOption> => {
    let { x, y } = tooltipModel;
    const { xAlign, yAlign } = tooltipModel;

    const elemWidth = element.clientWidth;
    const elemHeight = element.clientHeight;

    if (tooltipModel.xAlign === 'center')
      x += (tooltipModel.width - elemWidth) / 2;
    else if (tooltipModel.xAlign === 'right')
      x += tooltipModel.width - elemWidth;

    if (tooltipModel.yAlign === 'center')
      y += (tooltipModel.height - elemHeight) / 2;
    else if (tooltipModel.yAlign === 'bottom')
      y += tooltipModel.height - elemHeight;

    return {
      xAlign,
      yAlign,
      left: x,
      top: y,
      visible: true,
    };
  };

  return {
    tooltipDisplayOption,
    tooltipContent,
    calculateTooltipPosition,
  };
}
