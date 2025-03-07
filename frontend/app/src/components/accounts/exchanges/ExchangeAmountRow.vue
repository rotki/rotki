<script setup lang="ts">
import type { BigNumber } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import LocationDisplay from '@/components/history/LocationDisplay.vue';
import { useLocations } from '@/composables/locations';

const props = defineProps<{
  balance: BigNumber;
  exchange: string;
}>();

const { exchange } = toRefs(props);
const { exchangeName } = useLocations();

const name = computed<string>(() => {
  if (!get(exchange))
    return '';

  return exchangeName(exchange);
});
</script>

<template>
  <div class="flex items-center gap-3 w-full">
    <LocationDisplay
      v-if="exchange"
      :open-details="false"
      :identifier="exchange"
      size="1.5rem"
      icon
    />
    <div class="flex gap-3 items-center justify-between w-full">
      <span class="text-sm">
        {{ name }}
      </span>
      <AmountDisplay
        class="text-rui-text-secondary text-xs"
        show-currency="symbol"
        fiat-currency="USD"
        :value="balance"
      />
    </div>
  </div>
</template>
