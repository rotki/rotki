<script setup lang="ts">
import { type PropType } from 'vue';
import { type MakerDAOVaultModel } from '@/types/defi/maker';

const props = defineProps({
  vault: {
    required: true,
    type: Object as PropType<MakerDAOVaultModel>
  }
});

const { vault } = toRefs(props);
const { t } = useI18n();
const ratio = computed(() => {
  const { collateralizationRatio } = get(vault);
  return collateralizationRatio ? collateralizationRatio : null;
});
</script>

<template>
  <StatCard :title="t('loan_collateral.title')">
    <LoanRow :title="t('loan_collateral.locked_collateral')">
      <BalanceDisplay
        :asset="vault.collateral.asset"
        :value="vault.collateral"
      />
    </LoanRow>
    <VDivider class="my-4" />
    <LoanRow :title="t('loan_collateral.current_ratio')" class="mb-2">
      <PercentageDisplay :value="ratio" />
    </LoanRow>
    <ManageWatchers :vault="vault" />
  </StatCard>
</template>
