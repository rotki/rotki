import { type BigNumber } from '@rotki/common';
import { type Collateral, type CollateralizedLoan } from '@/types/defi';

export const totalCollateral = (
  loan: Ref<CollateralizedLoan<Collateral[]>>
): ComputedRef<BigNumber> =>
  computed(() =>
    get(loan).collateral.reduce(
      (previous, current) => previous.plus(current.usdValue),
      Zero
    )
  );
