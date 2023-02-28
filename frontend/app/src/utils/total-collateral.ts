import { type BigNumber } from '@rotki/common';
import { type ComputedRef, type Ref } from 'vue';
import { type Collateral, type CollateralizedLoan } from '@/types/defi';
import { Zero } from '@/utils/bignumbers';

export const totalCollateral = (
  loan: Ref<CollateralizedLoan<Collateral[]>>
): ComputedRef<BigNumber> => {
  return computed(() =>
    get(loan).collateral.reduce(
      (previous, current) => previous.plus(current.usdValue),
      Zero
    )
  );
};
