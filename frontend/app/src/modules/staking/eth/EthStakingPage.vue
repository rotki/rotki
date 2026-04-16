<script setup lang="ts">
import AccountFormApiKeyAlert from '@/modules/accounts/management/AccountFormApiKeyAlert.vue';
import { EthStaking } from '@/modules/premium/premium';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import ModuleNotActive from '@/modules/settings/modules/ModuleNotActive.vue';
import { useGeneralSettingsStore } from '@/modules/settings/use-general-settings-store';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import EthStakingHeaderActions from './components/EthStakingHeaderActions.vue';
import EthStakingPagePlaceholder from './components/EthStakingPagePlaceholder.vue';
import EthValidatorFilter from './components/EthValidatorFilter.vue';
import { useEthStakingAccess } from './use-eth-staking-access';
import { useEthStakingPerformance } from './use-eth-staking-performance';
import { useEthStakingRefresh } from './use-eth-staking-refresh';
import { useEthValidatorManagement } from './use-eth-validator-management';

const { t } = useI18n({ useScope: 'global' });

// Access control
const { allowed, enabled, module } = useEthStakingAccess();

// API key check (only when module is allowed and enabled)
const { getApiKey } = useExternalApiKeys();
const { beaconRpcEndpoint } = storeToRefs(useGeneralSettingsStore());

const missingApiKeyService = computed<'beaconchain' | 'consensusRpc' | undefined>(() => {
  if (!get(allowed) || !get(enabled)) {
    return undefined;
  }

  if (!getApiKey('beaconchain')) {
    if (!get(beaconRpcEndpoint)) {
      return 'consensusRpc';
    }

    return 'beaconchain';
  }

  return undefined;
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
        v-if="missingApiKeyService"
        :service="missingApiKeyService"
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
