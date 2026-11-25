import type { BigNumber } from '@rotki/common';
import { computed, type ComputedRef, type MaybeRefOrGetter, toValue } from 'vue';
import { normalizeScrambleMultiplier } from '@/modules/session/session-utils';

export interface ScramblerOptions {
  value: MaybeRefOrGetter<BigNumber>;
  enabled: MaybeRefOrGetter<boolean>;
  multiplier: MaybeRefOrGetter<number>;
}

export function useNumberScrambler(options: ScramblerOptions): ComputedRef<BigNumber> {
  return computed<BigNumber>(() => {
    const value = toValue(options.value);
    if (!toValue(options.enabled))
      return value;

    return value.multipliedBy(normalizeScrambleMultiplier(toValue(options.multiplier)));
  });
}
