<script setup lang="ts">
import { type HistoryEventEntry } from '@/types/history/events';
import { CURRENCY_USD } from '@/types/currencies';

const props = defineProps<{
  event: HistoryEventEntry;
}>();

const { event } = toRefs(props);
const { assetSymbol } = useAssetInfoRetrieval();

const { getEventType } = useHistoryEventMappings();

const showBalance = computed<boolean>(() => {
  const type = get(getEventType(event));
  return !type || !['approval', 'informational'].includes(type);
});

const eventAsset = useRefMap(event, ({ asset }) => asset);

const symbol = assetSymbol(eventAsset);
const { navigateToDetails } = useAssetPageNavigation(eventAsset);
</script>

<template>
  <div class="py-2 flex items-center gap-2">
    <AssetIcon
      size="32px"
      :identifier="event.asset"
      @click="navigateToDetails()"
    />
    <div v-if="showBalance" class="flex flex-col">
      <AmountDisplay :value="event.balance.amount" :asset="event.asset" />
      <AmountDisplay
        :key="event.timestamp"
        :amount="event.balance.amount"
        :value="event.balance.usdValue"
        :price-asset="event.asset"
        :fiat-currency="CURRENCY_USD"
        class="text-rui-text-secondary"
        :timestamp="event.timestamp"
        milliseconds
      />
    </div>
    <template v-else>
      {{ symbol }}
    </template>
  </div>
</template>
