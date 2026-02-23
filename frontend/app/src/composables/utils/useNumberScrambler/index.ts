import type { BigNumber } from '@rotki/common';
import type { ComputedRef, MaybeRefOrGetter } from 'vue';

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

    return value.multipliedBy(toValue(options.multiplier));
  });
}
