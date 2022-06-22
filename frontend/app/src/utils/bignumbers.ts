import { BigNumber } from '@rotki/common';
import { computed, Ref, unref } from '@vue/composition-api';

export function bigNumberify(value: string | number) {
  return new BigNumber(value);
}

export function bigNumberifyFromRef(
  value: Ref<string | number>
): Ref<BigNumber> {
  return computed(() => {
    return new BigNumber(unref(value));
  });
}

export const Zero = new BigNumber(0);
export const NoPrice = new BigNumber(-1);

export const sortDesc = (a: BigNumber, b: BigNumber) => b.minus(a).toNumber();
