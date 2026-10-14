<script setup lang="ts">
import AccountFormApiKeyAlert from '@/modules/accounts/management/AccountFormApiKeyAlert.vue';
import { EthStaking } from '@/modules/premium/premium';
import { useExternalApiKeys } from '@/modules/settings/api-keys/external/use-external-api-keys';
import ModuleNotActive from '@/modules/settings/modules/ModuleNotActive.vue';
import { useSetting } from '@/modules/settings/use-setting';
import TablePageLayout from '@/modules/shell/layout/TablePageLayout.vue';
import StakingLocationTitle from '@/modules/staking/components/StakingLocationTitle.vue';
import EthStakingFilterBar from './components/EthStakingFilterBar.vue';
import EthStakingHeaderActions from './components/EthStakingHeaderActions.vue';
import EthStakingPagePlaceholder from './components/EthStakingPagePlaceholder.vue';
import { useEthStakingAccess } from './use-eth-staking-access';
import { useEthStakingPageRefresh } from './use-eth-staking-page-refresh';
import { useEthStakingPerformance } from './use-eth-staking-performance';
import { useEthStakingRefresh } from './use-eth-staking-refresh';
import { useEthValidatorManagement } from './use-eth-validator-management';

const { allowed, enabled, module } = useEthStakingAccess();

// API key check (only when module is allowed and enabled)
const { getApiKey } = useExternalApiKeys();
const beaconRpcEndpoint = useSetting('beaconRpcEndpoint');

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

/**
 * Beaconcha.in only sharpens a page that already works, so it is an offer the user can put away.
 * A missing consensus RPC means there is no staking data at all, which is a fault and stays inline.
 */
const optionalApiKeyService = computed<'beaconchain' | undefined>(() =>
  get(missingApiKeyService) === 'beaconchain' ? 'beaconchain' : undefined,
);

const blockingApiKeyService = computed<'consensusRpc' | undefined>(() =>
  get(missingApiKeyService) === 'consensusRpc' ? 'consensusRpc' : undefined,
);

const {
  fetchValidatorsWithFilter,
  modelFilter,
  modelSelection,
  setTotal,
  total,
} = useEthValidatorManagement();

const {
  getPerformance,
  performance,
  performanceLoading,
  performancePagination,
  refreshPerformance,
} = useEthStakingPerformance();

const { refresh, refreshing: stakingRefreshing } = useEthStakingRefresh({
  getPerformance,
  refreshPerformance,
  setTotal,
});

const { chainName, refreshPage, refreshing, syncHistory, syncingHistory } = useEthStakingPageRefresh(refresh, stakingRefreshing);

onBeforeMount(async () => {
  if (get(enabled))
    await refresh(false);

  await fetchValidatorsWithFilter();
});
</script>

<template>
  <TablePageLayout child>
    <template #title>
      <StakingLocationTitle location="eth2" />
    </template>
    <template
      v-if="allowed && enabled"
      #buttons
    >
      <EthStakingHeaderActions
        :refreshing="refreshing"
        :syncing-history="syncingHistory"
        :chain-name="chainName"
        :optional-api-key-service="optionalApiKeyService"
        @refresh="refreshPage()"
        @sync-history="syncHistory()"
      />
    </template>

    <EthStakingPagePlaceholder v-if="!allowed" />
    <ModuleNotActive
      v-else-if="!enabled"
      :modules="[module]"
    />
    <template v-else>
      <AccountFormApiKeyAlert
        v-if="blockingApiKeyService"
        :service="blockingApiKeyService"
      />

      <EthStaking
        v-model:performance-pagination="performancePagination"
        v-model:filter="modelFilter"
        :refreshing="refreshing"
        :total="total"
        :accounts="modelSelection"
        :performance="performance"
        :performance-loading="performanceLoading"
      >
        <template #selection>
          <EthStakingFilterBar
            v-model="modelSelection"
            v-model:filter="modelFilter"
          />
        </template>
      </EthStaking>
    </template>
  </TablePageLayout>
</template>
