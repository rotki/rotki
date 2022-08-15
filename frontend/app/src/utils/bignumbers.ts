import { Balance, BigNumber } from '@rotki/common';
import { computed, Ref } from '@vue/composition-api';
import { get } from '@vueuse/core';

export function bigNumberify(value: string | number) {
  return new BigNumber(value);
}

export function bigNumberifyFromRef(
  value: Ref<string | number>
): Ref<BigNumber> {
  return computed(() => {
    const val = get(value);
    if (val === '') return Zero;
    return new BigNumber(val);
  });
}

export const Zero = new BigNumber(0);
export const One = new BigNumber(1);
export const NoPrice = new BigNumber(-1);

export const zeroBalance = (): Balance => {
  return {
    amount: Zero,
    usdValue: Zero
  };
};

export const sortDesc = (a: BigNumber, b: BigNumber) => b.minus(a).toNumber();
