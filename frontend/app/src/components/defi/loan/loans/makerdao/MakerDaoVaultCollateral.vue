<script setup lang="ts">
import ManageWatchers from '@/components/defi/loan/loans/makerdao/ManageWatchers.vue';
import PercentageDisplay from '@/components/display/PercentageDisplay.vue';
import LoanRow from '@/components/defi/loan/LoanRow.vue';
import BalanceDisplay from '@/components/display/BalanceDisplay.vue';
import StatCard from '@/components/display/StatCard.vue';
import type { MakerDAOVaultModel } from '@/types/defi/maker';

const props = defineProps<{
  vault: MakerDAOVaultModel;
}>();

const { vault } = toRefs(props);
const { t } = useI18n();
const ratio = computed(() => {
  const { collateralizationRatio } = get(vault);
  return collateralizationRatio || null;
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

    <RuiDivider class="my-4" />

    <LoanRow :title="t('loan_collateral.current_ratio')">
      <PercentageDisplay :value="ratio ? ratio : undefined" />
    </LoanRow>

    <ManageWatchers
      :vault="vault"
      class="mt-4"
    />
  </StatCard>
</template>
