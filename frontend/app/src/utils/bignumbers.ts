import { type Balance, BigNumber } from '@rotki/common';
import { type ComputedRef, type Ref } from 'vue';

export function bigNumberify(value: string | number): BigNumber {
  return new BigNumber(value);
}

export function bigNumberifyFromRef(
  value: Ref<string | number>
): ComputedRef<BigNumber> {
  return computed(() => {
    const val = get(value);
    if (val === '') {
      return Zero;
    }
    return bigNumberify(val);
  });
}

export const Zero = bigNumberify(0);
export const One = bigNumberify(1);
export const NoPrice = bigNumberify(-1);

export const zeroBalance = (): Balance => ({
  amount: Zero,
  usdValue: Zero
});

export const sortDesc = (a: BigNumber, b: BigNumber): number =>
  b.minus(a).toNumber();
