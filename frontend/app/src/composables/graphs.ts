import { BigNumber } from '@rotki/common';
import { TooltipDisplayOption } from '@rotki/common/lib/settings/graphs';
import { TooltipModel } from 'chart.js';
import { useTheme } from '@/composables/common';
import { assert } from '@/utils/assertions';
import { bigNumberify } from '@/utils/bignumbers';

export const useGraph = (canvasId: string) => {
  const getCanvasCtx = (): CanvasRenderingContext2D => {
    const canvas = document.getElementById(canvasId);
    assert(
      canvas && canvas instanceof HTMLCanvasElement,
      'Canvas could not be found'
    );
    const context = canvas.getContext('2d');
    assert(context, 'Context could not be found');
    return context;
  };

  const { theme, dark } = useTheme();

  const white = '#ffffff';
  const secondaryBlack = '#3f1300';

  const baseColor = computed(() => {
    const activeTheme = get(theme);
    const graphColor = activeTheme.currentTheme['graph'];
    return (graphColor ? graphColor : '#96DFD2') as string;
  });

  const fadeColor = computed(() => {
    const activeTheme = get(theme);
    const graphFade = activeTheme.currentTheme['graphFade'];
    return (graphFade ? graphFade : white) as string;
  });

  const gradient = computed(() => {
    const context = getCanvasCtx();
    const areaGradient = context.createLinearGradient(0, 0, 0, 150);
    areaGradient.addColorStop(0, get(baseColor));
    areaGradient.addColorStop(1, get(fadeColor));
    return areaGradient;
  });

  const secondaryColor = computed(() => {
    return get(dark) ? white : secondaryBlack;
  });

  const fontColor = computed(() => {
    return get(dark) ? white : 'rgba(0,0,0,.6)';
  });

  const gridColor = computed(() => {
    return get(dark) ? '#555' : '#ddd';
  });

  return {
    getCanvasCtx,
    baseColor,
    gradient,
    secondaryColor,
    fontColor,
    gridColor
  };
};

export type TooltipContent = {
  readonly time: string;
  readonly value: BigNumber;
};

export const useTooltip = (id: string) => {
  const getDefaultTooltipDisplayOption = (): TooltipDisplayOption => {
    return {
      visible: false,
      left: 0,
      top: 0,
      xAlign: 'left',
      yAlign: 'center',
      id
    };
  };

  const getDefaultTooltipContent = (): TooltipContent => ({
    time: '',
    value: bigNumberify(0)
  });

  const tooltipDisplayOption = ref<TooltipDisplayOption>(
    getDefaultTooltipDisplayOption()
  );
  const tooltipContent = ref<TooltipContent>(getDefaultTooltipContent());

  const calculateTooltipPosition = (
    element: HTMLElement,
    tooltipModel: TooltipModel<'line'>
  ): Partial<TooltipDisplayOption> => {
    let { x, y } = tooltipModel;
    const { xAlign, yAlign } = tooltipModel;

    const elemWidth = element.clientWidth;
    const elemHeight = element.clientHeight;

    if (tooltipModel.xAlign === 'center') {
      x += (tooltipModel.width - elemWidth) / 2;
    } else if (tooltipModel.xAlign === 'right') {
      x += tooltipModel.width - elemWidth;
    }

    if (tooltipModel.yAlign === 'center') {
      y += (tooltipModel.height - elemHeight) / 2;
    } else if (tooltipModel.yAlign === 'bottom') {
      y += tooltipModel.height - elemHeight;
    }

    return {
      xAlign,
      yAlign,
      left: x,
      top: y,
      visible: true
    };
  };

  return {
    tooltipDisplayOption,
    tooltipContent,
    calculateTooltipPosition
  };
};
