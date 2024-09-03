import type { BigNumber } from '@rotki/common';
import type { Collateral, CollateralizedLoan } from '@/types/defi';

export function totalCollateral(loan: Ref<CollateralizedLoan<Collateral[]>>): ComputedRef<BigNumber> {
  return computed<BigNumber>(() => get(loan).collateral.reduce((previous, current) => previous.plus(current.usdValue), Zero));
}
