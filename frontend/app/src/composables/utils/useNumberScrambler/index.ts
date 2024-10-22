import type { BigNumber } from '@rotki/common';
import type { ComputedRef, Ref } from 'vue';

export interface ScramblerOptions {
  value: Ref<BigNumber>;
  enabled: Ref<boolean>;
  multiplier: Ref<number>;
}

export function useNumberScrambler(options: ScramblerOptions): ComputedRef<BigNumber> {
  return computed(() => {
    const value = get(options.value);
    if (!get(options.enabled))
      return value;

    return value.multipliedBy(get(options.multiplier));
  });
}
