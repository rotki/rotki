import type { Ref } from 'vue';
import { type BigNumber, Zero } from '@rotki/common';

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
