import { type BigNumber } from '@rotki/common';

export interface ScramblerOptions {
  value: Ref<BigNumber>;
  enabled: Ref<boolean>;
  multiplier: Ref<number>;
}
export const useNumberScrambler = (
  options: ScramblerOptions
): ComputedRef<BigNumber> =>
  computed(() => {
    const value = get(options.value);
    if (!get(options.enabled)) {
      return value;
    }
    return value.multipliedBy(get(options.multiplier));
  });
