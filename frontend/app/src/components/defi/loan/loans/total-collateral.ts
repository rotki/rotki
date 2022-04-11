import { computed, Ref } from '@vue/composition-api';
import { get } from '@vueuse/core';
import { Collateral, CollateralizedLoan } from '@/store/defi/types';
import { Zero } from '@/utils/bignumbers';

export const totalCollateral = (
  loan: Ref<CollateralizedLoan<Collateral<string>[]>>
) => {
  return computed(() =>
    get(loan)
      .collateral.map(({ usdValue }) => usdValue)
      .reduce((previous, current) => previous.plus(current), Zero)
  );
};
