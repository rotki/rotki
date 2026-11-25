import { type BigNumber, Zero } from '@rotki/common';
import { get, set } from '@vueuse/shared';
import { type Ref, ref } from 'vue';

export interface TooltipData {
  visible: boolean;
  x: number;
  y: number;
  timestamp: number;
  value: BigNumber;
  currentBalance: boolean;
}

interface UseGraphTooltipReturn {
  modelTooltipData: Ref<TooltipData>;
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

  const modelTooltipData = ref<TooltipData>(defaultTooltipData());

  function resetTooltipData(): void {
    set(modelTooltipData, {
      ...get(modelTooltipData),
      visible: false,
    });
  }

  return {
    resetTooltipData,
    modelTooltipData,
  };
}
