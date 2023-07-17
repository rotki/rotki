<script setup lang="ts">
import { DefiProtocol } from '@rotki/common/lib/blockchain';
import { type PropType } from 'vue';
import { type AaveLoan } from '@/types/defi/lending';
import { type CompoundLoan } from '@/types/defi/compound';
import { type MakerDAOVaultModel } from '@/types/defi/maker';
import { type LiquityLoan } from '@/types/defi/liquity';

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
    const currentLoan = get(loan);
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

<template>
  <MakerDaoVaultLoan v-if="vault" :vault="vault" />
  <AaveLending v-else-if="aaveLoan" :loan="aaveLoan" />
  <CompoundLending v-else-if="compoundLoan" :loan="compoundLoan" />
  <LiquityLending v-else-if="liquityLoan" :loan="liquityLoan" />
</template>
