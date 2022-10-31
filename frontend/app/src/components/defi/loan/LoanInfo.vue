<template>
  <maker-dao-vault-loan v-if="vault" :vault="vault" />
  <aave-lending v-else-if="aaveLoan" :loan="aaveLoan" />
  <compound-lending v-else-if="compoundLoan" :loan="compoundLoan" />
  <liquity-lending v-else-if="liquityLoan" :loan="liquityLoan" />
</template>

<script setup lang="ts">
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { PropType } from 'vue';
import AaveLending from '@/components/defi/loan/loans/AaveLending.vue';
import CompoundLending from '@/components/defi/loan/loans/CompoundLending.vue';
import LiquityLending from '@/components/defi/loan/loans/LiquityLending.vue';
import MakerDaoVaultLoan from '@/components/defi/loan/loans/MakerDaoVaultLoan.vue';
import { LiquityLoan } from '@/store/defi/liquity/types';
import { AaveLoan } from '@/store/defi/types';
import { CompoundLoan } from '@/types/defi/compound';
import { MakerDAOVaultModel } from '@/types/defi/maker';

type Loan = MakerDAOVaultModel | AaveLoan | CompoundLoan | LiquityLoan;

const props = defineProps({
  loan: {
    required: true,
    type: Object as PropType<Loan>
  }
});

const { loan } = toRefs(props);

const create = <T extends Loan>(protocol: DefiProtocol) =>
  computed<T | null>(() => {
    let currentLoan = get(loan);
    if (currentLoan.protocol === protocol) {
      return currentLoan as T;
    }
    return null;
  });

const vault = create<MakerDAOVaultModel>(DefiProtocol.MAKERDAO_VAULTS);
const aaveLoan = create<AaveLoan>(DefiProtocol.AAVE);
const compoundLoan = create<CompoundLoan>(DefiProtocol.COMPOUND);
const liquityLoan = create<LiquityLoan>(DefiProtocol.LIQUITY);
</script>
