<script setup lang="ts">
import { DefiProtocol } from '@/types/modules';
import LiquityLending from '@/components/defi/loan/loans/LiquityLending.vue';
import CompoundLending from '@/components/defi/loan/loans/CompoundLending.vue';
import AaveLending from '@/components/defi/loan/loans/AaveLending.vue';
import MakerDaoVaultLoan from '@/components/defi/loan/loans/MakerDaoVaultLoan.vue';
import type { AaveLoan } from '@/types/defi/lending';
import type { CompoundLoan } from '@/types/defi/compound';
import type { MakerDAOVaultModel } from '@/types/defi/maker';
import type { LiquityLoan } from '@/types/defi/liquity';

type Loan = MakerDAOVaultModel | AaveLoan | CompoundLoan | LiquityLoan;

const props = defineProps<{ loan: Loan }>();

const { loan } = toRefs(props);

function create<T extends Loan>(protocol: DefiProtocol) {
  return computed<T | null>(() => {
    const currentLoan = get(loan);
    if (currentLoan.protocol === protocol)
      return currentLoan as T;

    return null;
  });
}

const vault = create<MakerDAOVaultModel>(DefiProtocol.MAKERDAO_VAULTS);
const aaveLoan = create<AaveLoan>(DefiProtocol.AAVE);
const compoundLoan = create<CompoundLoan>(DefiProtocol.COMPOUND);
const liquityLoan = create<LiquityLoan>(DefiProtocol.LIQUITY);
</script>

<template>
  <MakerDaoVaultLoan
    v-if="vault"
    :vault="vault"
  />
  <AaveLending
    v-else-if="aaveLoan"
    :loan="aaveLoan"
  />
  <CompoundLending
    v-else-if="compoundLoan"
    :loan="compoundLoan"
  />
  <LiquityLending
    v-else-if="liquityLoan"
    :loan="liquityLoan"
  />
</template>
