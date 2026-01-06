<script setup lang="ts">
import DateDisplay from '@/components/display/DateDisplay.vue';
import HistoryEventsAlert from '@/components/history/HistoryEventsAlert.vue';
import HistoricalBalancesFilter from '@/modules/history/balances/HistoricalBalancesFilter.vue';
import HistoricalBalancesTable from '@/modules/history/balances/HistoricalBalancesTable.vue';
import { useHistoricalBalances } from '@/modules/history/balances/use-historical-balances';

const { t } = useI18n({ useScope: 'global' });

const {
  balances,
  errorMessage,
  fetchBalances,
  hasResults,
  loading,
  noDataFound,
  queriedTimestamp,
  selectedAsset,
  selectedLocation,
  selectedLocationLabel,
  selectedProtocol,
  timestamp,
} = useHistoricalBalances();
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
    />

    <RuiButton
      color="primary"
      :loading="loading"
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
