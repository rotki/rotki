<script setup lang="ts">
import { type AssetBalance, HistoryEventEntryType } from '@rotki/common';
import { useKrakenStakingStore } from '@/store/staking/kraken';
import HistoryEventsView from '@/components/history/events/HistoryEventsView.vue';
import KrakenStakingReceived from '@/components/staking/kraken/KrakenStakingReceived.vue';
import KrakenStakingOverview from '@/components/staking/kraken/KrakenStakingOverview.vue';
import KrakenDateFilter from '@/components/staking/kraken/KrakenDateFilter.vue';
import { useBalancePricesStore } from '@/store/balances/prices';
import type { KrakenStakingDateFilter } from '@/types/staking';

const modelValue = defineModel<KrakenStakingDateFilter>({ required: true });

const { events } = toRefs(useKrakenStakingStore());
const { assetPrice } = useBalancePricesStore();

const earnedAssetsData = computed<[boolean, AssetBalance[]]>(() => {
  const earned = get(events).received;

  let loading = false;

  const earnedWithPrice = earned.map((item) => {
    const price = get(assetPrice(item.asset));
    if (!price) {
      loading = true;

      return item;
    }
    return {
      ...item,
      usdValue: price.times(item.amount),
    };
  });

  return [loading, earnedWithPrice];
});
</script>

<template>
  <div class="flex flex-col gap-4">
    <div class="flex justify-end">
      <div class="w-full md:w-1/2 md:-mr-2">
        <KrakenDateFilter
          v-model="modelValue"
        />
      </div>
    </div>
    <div class="grid md:grid-cols-2 gap-4">
      <KrakenStakingOverview
        :loading="earnedAssetsData[0]"
        :total-usd-historical="events.totalUsdValue"
        :earned="earnedAssetsData[1]"
      />
      <KrakenStakingReceived
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
