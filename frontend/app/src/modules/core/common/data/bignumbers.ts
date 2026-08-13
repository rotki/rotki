import type { ComputedRef, MaybeRefOrGetter } from 'vue';
import { type Balance, type BigNumber, bigNumberify, Zero } from '@rotki/common';

export function bigNumberifyFromRef(value: MaybeRefOrGetter<string | number>): ComputedRef<BigNumber> {
  return computed(() => {
    const val = toValue(value);
    // Cheap path for a cleared field, which is common enough not to reach it through a throw.
    if (val === '')
      return Zero;

    // bignumber.js rejects anything it cannot parse by throwing, and this runs inside a computed,
    // so an unparsable value would surface as a render-time exception rather than a bad number.
    return bigNumberify(val, Zero);
  });
}

export function zeroBalance(): Balance {
  return {
    amount: Zero,
    value: Zero,
  };
}

export function sortDesc(a: BigNumber, b: BigNumber): number {
  return b.minus(a).toNumber();
}
