<script setup lang="ts">
import { type AaveLoan } from '@/types/defi/lending';
import { type CompoundLoan } from '@/types/defi/compound';
import { type MakerDAOVaultModel } from '@/types/defi/maker';
import { type LiquityLoan } from '@/types/defi/liquity';
import { Module } from '@/types/modules';

type Loan = MakerDAOVaultModel | AaveLoan | CompoundLoan | LiquityLoan;

const props = defineProps<{ loan: Loan }>();

const { loan } = toRefs(props);

const create = <T extends Loan>(protocol: Module) =>
  computed<T | null>(() => {
    const currentLoan = get(loan);
    if (currentLoan.protocol === protocol) {
      return currentLoan as T;
    }
    return null;
  });

const vault = create<MakerDAOVaultModel>(Module.MAKERDAO_VAULTS);
const aaveLoan = create<AaveLoan>(Module.AAVE);
const compoundLoan = create<CompoundLoan>(Module.COMPOUND);
const liquityLoan = create<LiquityLoan>(Module.LIQUITY);
</script>

<template>
  <MakerDaoVaultLoan v-if="vault" :vault="vault" />
  <AaveLending v-else-if="aaveLoan" :loan="aaveLoan" />
  <CompoundLending v-else-if="compoundLoan" :loan="compoundLoan" />
  <LiquityLending v-else-if="liquityLoan" :loan="liquityLoan" />
</template>
