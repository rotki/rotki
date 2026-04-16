import type { BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { useNumberScrambler } from '@/modules/assets/amount-display/use-number-scrambler';
import { generateRandomScrambleMultiplier } from '@/modules/session/session-utils';
import { useAmountDisplaySettings } from './use-amount-display-settings';

export interface UseScrambledValueOptions {
  value: MaybeRefOrGetter<BigNumber>;
  noScramble?: MaybeRefOrGetter<boolean>;
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
  const { value, noScramble } = options;

  const {
    scrambleData,
    scrambleMultiplier: scrambleMultiplierRef,
    shouldShowAmount,
  } = useAmountDisplaySettings();

  const scrambleMultiplier = ref<number>(get(scrambleMultiplierRef) ?? generateRandomScrambleMultiplier());

  const scrambledValue = useNumberScrambler({
    enabled: computed<boolean>(() => !toValue(noScramble) && (get(scrambleData) || !get(shouldShowAmount))),
    multiplier: scrambleMultiplier,
    value,
  });

  watchEffect(() => {
    const newValue = get(scrambleMultiplierRef);
    if (newValue !== undefined) {
      set(scrambleMultiplier, newValue);
    }
  });

  return {
    scrambledValue,
  };
}
