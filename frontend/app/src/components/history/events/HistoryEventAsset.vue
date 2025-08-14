<script setup lang="ts">
import type { HistoryEventEntry } from '@/types/history/events/schemas';
import { Zero } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import AssetDetails from '@/components/helper/AssetDetails.vue';
import { useAssetInfoRetrieval } from '@/composables/assets/retrieval';
import { useRefMap } from '@/composables/utils/useRefMap';
import { CURRENCY_USD } from '@/types/currencies';

const props = defineProps<{
  event: HistoryEventEntry;
}>();

const emit = defineEmits<{
  refresh: [];
}>();

const { event } = toRefs(props);
const { assetSymbol } = useAssetInfoRetrieval();

const showBalance = computed<boolean>(() => get(event).eventType !== 'informational');

const eventAsset = useRefMap(event, ({ asset }) => asset);

const symbol = assetSymbol(eventAsset, {
  collectionParent: false,
});
</script>

<template>
  <div class="py-2 flex items-center gap-2">
    <AssetDetails
      size="32px"
      icon-only
      :asset="event.asset"
      :resolution-options="{
        collectionParent: false,
      }"
      @refresh="emit('refresh')"
    />
    <div
      v-if="showBalance"
      class="flex flex-col"
    >
      <AmountDisplay
        :value="event.amount"
        :asset="event.asset"
        :resolution-options="{
          collectionParent: false,
        }"
      />
      <AmountDisplay
        :key="event.timestamp"
        :amount="event.amount"
        :value="Zero"
        :price-asset="event.asset"
        :fiat-currency="CURRENCY_USD"
        class="text-rui-text-secondary"
        :timestamp="event.timestamp"
        milliseconds
      />
    </div>
    <div
      v-else
      class="text-truncate"
    >
      {{ symbol }}
    </div>
  </div>
</template>
