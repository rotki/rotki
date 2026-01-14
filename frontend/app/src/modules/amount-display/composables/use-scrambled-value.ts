import type { BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRef } from 'vue';
import { useNumberScrambler } from '@/composables/utils/useNumberScrambler';
import { generateRandomScrambleMultiplier } from '@/utils/session';
import { useAmountDisplaySettings } from './use-amount-display-settings';

export interface UseScrambledValueOptions {
  value: MaybeRef<BigNumber>;
}

export interface UseScrambledValueReturn {
  /** The scrambled value (when scrambling is enabled in settings) */
  scrambledValue: ComputedRef<BigNumber>;
}

/**
 * Applies scrambling to a value for privacy when enabled in user settings.
 * Use this for personal values (balances, totals) - not for prices.
 */
export function useScrambledValue(options: UseScrambledValueOptions): UseScrambledValueReturn {
  const { value } = options;

  const {
    scrambleData,
    scrambleMultiplier: scrambleMultiplierRef,
    shouldShowAmount,
  } = useAmountDisplaySettings();

  const scrambleMultiplier = ref<number>(get(scrambleMultiplierRef) ?? generateRandomScrambleMultiplier());

  watchEffect(() => {
    const newValue = get(scrambleMultiplierRef);
    if (newValue !== undefined) {
      set(scrambleMultiplier, newValue);
    }
  });

  const valueRef = isRef(value) ? value : ref(value);

  const scrambledValue = useNumberScrambler({
    enabled: computed<boolean>(() => get(scrambleData) || !get(shouldShowAmount)),
    multiplier: scrambleMultiplier,
    value: valueRef as ComputedRef<BigNumber>,
  });

  return {
    scrambledValue,
  };
}
