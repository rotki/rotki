<script setup lang="ts">
import { type PropType } from 'vue';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import ManageWatchers from '@/components/defi/loan/loans/makerdao/ManageWatchers.vue';
import StatCard from '@/components/display/StatCard.vue';
import { type MakerDAOVaultModel } from '@/types/defi/maker';

const props = defineProps({
  vault: {
    required: true,
    type: Object as PropType<MakerDAOVaultModel>
  }
});

const { vault } = toRefs(props);
const { tc } = useI18n();
const ratio = computed(() => {
  const { collateralizationRatio } = get(vault);
  return collateralizationRatio ? collateralizationRatio : null;
});
</script>

<template>
  <stat-card :title="tc('loan_collateral.title')">
    <loan-row :title="tc('loan_collateral.locked_collateral')">
      <balance-display
        :asset="vault.collateral.asset"
        :value="vault.collateral"
      />
    </loan-row>
    <v-divider class="my-4" />
    <loan-row :title="tc('loan_collateral.current_ratio')" class="mb-2">
      <percentage-display :value="ratio" />
    </loan-row>
    <manage-watchers :vault="vault" />
  </stat-card>
</template>
