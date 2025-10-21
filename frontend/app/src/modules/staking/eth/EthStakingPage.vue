<script setup lang="ts">
import AccountFormApiKeyAlert from '@/components/accounts/management/AccountFormApiKeyAlert.vue';
import ModuleNotActive from '@/components/defi/ModuleNotActive.vue';
import TablePageLayout from '@/components/layout/TablePageLayout.vue';
import { useExternalApiKeys } from '@/composables/settings/api-keys/external';
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
const { allowed, enabled, module } = useEthStakingAccess();

// API key check (only when module is allowed and enabled)
const { apiKey } = useExternalApiKeys(t);
const hasBeaconchainApiKey = computed<boolean>(() => {
  if (!get(allowed) || !get(enabled)) {
    return true;
  }

  return !!get(apiKey('beaconchain'));
});

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
    <EthStakingPagePlaceholder v-if="!allowed" />
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

      <AccountFormApiKeyAlert
        v-if="!hasBeaconchainApiKey"
        service="beaconchain"
      />

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
