import type { Balance, BigNumber } from '@rotki/common';
import type { ComputedRef, Ref, WritableComputedRef } from 'vue';

export function bigNumberifyFromRef(value: Ref<string | number> | WritableComputedRef<string | number>): ComputedRef<BigNumber> {
  return computed(() => {
    const val = get(value);
    if (val === '')
      return Zero;

    return bigNumberify(val);
  });
}

export function zeroBalance(): Balance {
  return {
    amount: Zero,
    usdValue: Zero,
  };
}

export function sortDesc(a: BigNumber, b: BigNumber): number {
  return b.minus(a).toNumber();
}
