import type { ComputedRef, Ref, WritableComputedRef } from 'vue';
import { type Balance, type BigNumber, bigNumberify, Zero } from '@rotki/common';

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
    value: Zero,
  };
}

export function sortDesc(a: BigNumber, b: BigNumber): number {
  return b.minus(a).toNumber();
}
