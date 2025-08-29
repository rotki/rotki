<script setup lang="ts">
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { EthStaking } from '@/premium/premium';
import EthStakingHeaderActions from './components/EthStakingHeaderActions.vue';
import EthStakingPagePlaceholder from './components/EthStakingPagePlaceholder.vue';
import EthValidatorFilter from './components/EthValidatorFilter.vue';
import { useEthStakingAccess } from './composables/use-eth-staking-access';
import { useEthStakingPerformance } from './composables/use-eth-staking-performance';
import { useEthStakingRefresh } from './composables/use-eth-staking-refresh';
import { useEthValidatorManagement } from './composables/use-eth-validator-management';

const { t } = useI18n({ useScope: 'global' });

// Access control
const { enabled, module, premium } = useEthStakingAccess();

// Validator management
const {
  fetchValidatorsWithFilter,
  filter,
  selection,
  setTotal,
  total,
} = useEthValidatorManagement();

// Performance management
const {
  getPerformance,
  performance,
  performanceLoading,
  performancePagination,
  refreshPerformance,
} = useEthStakingPerformance();

// Refresh and loading states
const { refresh, refreshing } = useEthStakingRefresh({
  getPerformance,
  refreshPerformance,
  setTotal,
});

onBeforeMount(async () => {
  if (get(enabled))
    await refresh(false);

  await fetchValidatorsWithFilter();
});
</script>

<template>
  <div>
    <EthStakingPagePlaceholder v-if="!premium" />
    <ModuleNotActive
      v-else-if="!enabled"
      :modules="[module]"
    />

    <TablePageLayout
      v-else
      :title="[t('navigation_menu.staking'), t('staking.eth2')]"
      child
    >
      <template #buttons>
        <EthStakingHeaderActions
          :refreshing="refreshing"
          @refresh="refresh(true)"
        />
      </template>

      <EthStaking
        v-model:performance-pagination="performancePagination"
        v-model:filter="filter"
        :refreshing="refreshing"
        :total="total"
        :accounts="selection"
        :performance="performance"
        :performance-loading="performanceLoading"
      >
        <template #selection>
          <EthValidatorFilter
            v-model="selection"
            v-model:filter="filter"
          />
        </template>
      </EthStaking>
    </TablePageLayout>
  </div>
</template>
