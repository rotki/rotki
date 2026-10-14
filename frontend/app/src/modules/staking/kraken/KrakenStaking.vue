<script setup lang="ts">
import type { KrakenStakingDateFilter } from '@/modules/staking/staking-types';
import { type AssetBalance, type BigNumber, HistoryEventEntryType } from '@rotki/common';
import { usePriceUtils } from '@/modules/assets/prices/use-price-utils';
import { sum } from '@/modules/core/common/display/balances';
import HistoryEventsView from '@/modules/history/events/HistoryEventsView.vue';
import KrakenDateFilter from '@/modules/staking/kraken/KrakenDateFilter.vue';
import KrakenStakingOverview from '@/modules/staking/kraken/KrakenStakingOverview.vue';
import KrakenStakingReceived from '@/modules/staking/kraken/KrakenStakingReceived.vue';
import { useKrakenStakingStore } from '@/modules/staking/use-kraken-staking-store';

const modelValue = defineModel<KrakenStakingDateFilter>({ required: true });

const { t } = useI18n({ useScope: 'global' });

const selection = ref<'current' | 'historical'>('current');

const { events } = storeToRefs(useKrakenStakingStore());
const { getAssetPrice } = usePriceUtils();

interface PricedEarnings {
  /** Whether a current price is still missing for some asset. */
  pricing: boolean;
  earned: AssetBalance[];
}

/**
 * The earned assets at their current prices, whatever the per-asset list shows: the overview's
 * current total is read from these, and it used to follow the list's toggle into historical values.
 */
const currentEarnings = computed<PricedEarnings>(() => {
  let pricing = false;
  const earned = get(events).received.map((item) => {
    const price = getAssetPrice(item.asset);
    if (!price || price.lte(0)) {
      pricing = true;
      return item;
    }
    return { ...item, value: price.times(item.amount) };
  });
  return { earned, pricing };
});

const totalCurrent = computed<BigNumber>(() => sum(get(currentEarnings).earned));

const shownEarnings = computed<AssetBalance[]>(() =>
  get(selection) === 'historical' ? get(events).received : get(currentEarnings).earned);
</script>

<template>
  <div class="flex flex-col gap-4">
    <KrakenDateFilter v-model="modelValue" />

    <div class="grid md:grid-cols-2 gap-4 items-start">
      <KrakenStakingOverview
        :loading="currentEarnings.pricing"
        :total-historical="events.totalValue"
        :total-current="totalCurrent"
        :rewards-count="events.entriesFound"
      />
      <KrakenStakingReceived
        v-model="selection"
        :loading="currentEarnings.pricing"
        :received="shownEarnings"
      />
    </div>

    <HistoryEventsView
      :section-title="t('common.events')"
      :restrictions="{
        entryTypes: [HistoryEventEntryType.HISTORY_EVENT],
        eventTypes: ['staking'],
        // Kraken has no per-account axis to offer, but it owns the one there is.
        externalAccounts: [],
        location: 'kraken',
        period: modelValue,
      }"
    />
  </div>
</template>
