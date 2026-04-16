<script setup lang="ts">
import type { KrakenStakingDateFilter } from '@/modules/staking/staking-types';
import { type AssetBalance, HistoryEventEntryType } from '@rotki/common';
import { useHistoricCachePriceStore } from '@/modules/assets/prices/use-historic-cache-price-store';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import HistoryEventsView from '@/modules/history/events/HistoryEventsView.vue';
import KrakenDateFilter from '@/modules/staking/kraken/KrakenDateFilter.vue';
import KrakenStakingOverview from '@/modules/staking/kraken/KrakenStakingOverview.vue';
import KrakenStakingReceived from '@/modules/staking/kraken/KrakenStakingReceived.vue';
import { useKrakenStakingStore } from '@/modules/staking/use-kraken-staking-store';

const modelValue = defineModel<KrakenStakingDateFilter>({ required: true });

defineProps<{
  loading: boolean;
}>();

const { t } = useI18n({ useScope: 'global' });

const selection = ref<'current' | 'historical'>('current');

const { events } = storeToRefs(useKrakenStakingStore());
const { getAssetPrice } = usePriceUtils();

const { getProtocolStatsPriceQueryStatus } = useHistoricCachePriceStore();
const krakenHistoricPriceStatus = getProtocolStatsPriceQueryStatus('kraken');

const earnedAssetsData = computed<[boolean, AssetBalance[]]>(() => {
  const earned = get(events).received;

  if (get(selection) === 'historical') {
    return [false, earned];
  }

  let loading = false;

  const earnedWithPrice = earned.map((item) => {
    const price = getAssetPrice(item.asset);
    if (!price) {
      loading = true;

      return item;
    }
    return {
      ...item,
      value: price.times(item.amount),
    };
  });

  return [loading, earnedWithPrice];
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="grid md:grid-cols-2 gap-x-4 gap-y-2">
      <KrakenDateFilter v-model="modelValue" />

      <div
        v-if="loading && krakenHistoricPriceStatus"
        class="flex items-center gap-2 text-rui-text-secondary text-sm"
      >
        <RuiProgress
          thickness="2"
          size="18"
          color="primary"
          variant="indeterminate"
          circular
        />
        {{ t('kraken_staking_events.query_historical_price', {
          processed: krakenHistoricPriceStatus.processed,
          total: krakenHistoricPriceStatus.total,
        }) }}
      </div>
    </div>
    <div class="grid md:grid-cols-2 gap-4">
      <KrakenStakingOverview
        :loading="earnedAssetsData[0]"
        :total-historical="events.totalValue"
        :earned="earnedAssetsData[1]"
      />
      <KrakenStakingReceived
        v-model="selection"
        :loading="earnedAssetsData[0]"
        :received="earnedAssetsData[1]"
      />
    </div>

    <!-- as an exception here we specify event-types to only include staking events  -->
    <!-- if an alternative way becomes possible we can use that -->
    <HistoryEventsView
      use-external-account-filter
      location="kraken"
      :period="modelValue"
      :event-types="['staking']"
      :entry-types="[HistoryEventEntryType.HISTORY_EVENT]"
    />
  </div>
</template>
