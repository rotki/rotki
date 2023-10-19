<script setup lang="ts">
import { type MakerDAOVaultModel } from '@/types/defi/maker';

const props = defineProps<{
  vault: MakerDAOVaultModel;
}>();

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

    <div class="my-4 border-b dark:border-rui-grey-800" />

    <LoanRow :title="t('loan_collateral.current_ratio')" class="mb-2">
      <PercentageDisplay :value="ratio" />
    </LoanRow>
    <ManageWatchers :vault="vault" />
  </StatCard>
</template>
