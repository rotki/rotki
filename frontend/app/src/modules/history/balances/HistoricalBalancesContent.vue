<script setup lang="ts">
import { startPromise } from '@shared/utils';
import DateDisplay from '@/components/display/DateDisplay.vue';
import InternalLink from '@/components/helper/InternalLink.vue';
import HistoryEventsAlert from '@/components/history/HistoryEventsAlert.vue';
import { useSupportedChains } from '@/composables/info/chains';
import HistoricalBalancesFilter from '@/modules/history/balances/HistoricalBalancesFilter.vue';
import HistoricalBalancesTable from '@/modules/history/balances/HistoricalBalancesTable.vue';
import { HistoricalBalanceSource } from '@/modules/history/balances/types';
import { useArchiveNodes } from '@/modules/history/balances/use-archive-nodes';
import { useHistoricalBalances } from '@/modules/history/balances/use-historical-balances';
import { Routes } from '@/router/routes';

const { t } = useI18n({ useScope: 'global' });

const {
  balances,
  errorMessage,
  fetchBalances,
  fieldErrors,
  hasResults,
  hasSavedFilters,
  loading,
  noDataFound,
  queriedTimestamp,
  selectedAccount,
  selectedAsset,
  selectedLocation,
  selectedLocationLabel,
  selectedProtocol,
  source,
  timestamp,
} = useHistoricalBalances();

const {
  chainsWithArchiveNodes,
  loading: loadingArchiveNodes,
  refresh: refreshArchiveNodes,
} = useArchiveNodes();

const { getChainName } = useSupportedChains();

const isArchiveNodeSource = computed<boolean>(() => get(source) === HistoricalBalanceSource.ARCHIVE_NODE);

const noArchiveNodesAtAll = computed<boolean>(() =>
  get(isArchiveNodeSource) && !get(loadingArchiveNodes) && get(chainsWithArchiveNodes).length === 0,
);

const selectedChainMissingArchiveNode = computed<boolean>(() => {
  if (!get(isArchiveNodeSource) || get(loadingArchiveNodes))
    return false;

  const account = get(selectedAccount);
  if (!account)
    return false;

  return !get(chainsWithArchiveNodes).includes(account.chain);
});

const selectedChainName = computed<string>(() => {
  const account = get(selectedAccount);
  if (!account)
    return '';

  return get(getChainName(account.chain));
});

const chainSettingsRoute = computed(() => {
  const account = get(selectedAccount);
  if (!account)
    return Routes.SETTINGS_RPC;

  return {
    path: Routes.SETTINGS_RPC.toString(),
    query: { tab: account.chain },
  };
});

const archiveNodeUnavailable = computed<boolean>(() =>
  get(noArchiveNodesAtAll) || get(selectedChainMissingArchiveNode),
);

onMounted(() => {
  refreshArchiveNodes();

  // Auto-fetch if there are saved filters from a previous query
  if (get(hasSavedFilters))
    startPromise(fetchBalances());
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <HistoryEventsAlert />

    <HistoricalBalancesFilter
      v-model:timestamp="timestamp"
      v-model:selected-asset="selectedAsset"
      v-model:selected-location="selectedLocation"
      v-model:selected-location-label="selectedLocationLabel"
      v-model:selected-protocol="selectedProtocol"
      v-model:source="source"
      v-model:selected-account="selectedAccount"
      :field-errors="fieldErrors"
    />

    <div class="flex flex-col gap-1">
      <RuiButton
        color="primary"
        :loading="loading"
        :disabled="archiveNodeUnavailable"
        size="lg"
        @click="fetchBalances()"
      >
        <template #prepend>
          <RuiIcon
            name="lu-search"
            size="20"
          />
        </template>
        {{ t('historical_balances.fetch_button') }}
      </RuiButton>
      <div
        v-if="isArchiveNodeSource && loadingArchiveNodes"
        class="text-rui-text-secondary text-caption"
      >
        {{ t('historical_balances.source.loading_archive_nodes') }}
      </div>
      <div
        v-else-if="noArchiveNodesAtAll"
        class="text-rui-text-secondary text-caption"
      >
        <i18n-t
          keypath="historical_balances.source.no_archive_nodes"
          tag="span"
        >
          <template #link>
            <InternalLink :to="Routes.SETTINGS_RPC">
              {{ t('historical_balances.source.settings_link') }}
            </InternalLink>
          </template>
        </i18n-t>
      </div>
      <div
        v-else-if="selectedChainMissingArchiveNode"
        class="text-rui-text-secondary text-caption"
      >
        <i18n-t
          keypath="historical_balances.source.chain_missing_archive_node"
          tag="span"
        >
          <template #chain>
            {{ selectedChainName }}
          </template>
          <template #link>
            <InternalLink :to="chainSettingsRoute">
              {{ t('historical_balances.source.settings_link') }}
            </InternalLink>
          </template>
        </i18n-t>
      </div>
    </div>

    <RuiAlert
      v-if="errorMessage"
      type="error"
    >
      {{ errorMessage }}
    </RuiAlert>

    <RuiAlert
      v-if="noDataFound"
      type="info"
    >
      {{ t('historical_balances.no_data') }}
    </RuiAlert>

    <template v-if="hasResults">
      <RuiDivider class="my-2" />

      <div class="text-subtitle-2 text-rui-text-secondary">
        {{ t('historical_balances.results_timestamp') }}
        <DateDisplay
          v-if="queriedTimestamp"
          :timestamp="queriedTimestamp"
        />
      </div>

      <HistoricalBalancesTable
        :balances="balances"
        :loading="loading"
        :timestamp="queriedTimestamp"
      />
    </template>
  </div>
</template>
