<script setup lang="ts">
import { type BigNumber } from '@rotki/common';

const props = defineProps<{
  balance: BigNumber;
  exchange: string;
}>();

const { exchange } = toRefs(props);
const { exchangeName } = useLocations();

const name = computed<string>(() => {
  if (!get(exchange)) {
    return '';
  }
  return exchangeName(exchange);
});
</script>

<template>
  <div class="flex items-center gap-4">
    <LocationDisplay
      v-if="exchange"
      :open-details="false"
      :identifier="exchange"
      size="32px"
      icon
    />
    <div class="flex flex-col my-3">
      <span class="text-h6">
        {{ name }}
      </span>
      <AmountDisplay
        class="text-rui-text-secondary"
        show-currency="symbol"
        fiat-currency="USD"
        :value="balance"
      />
    </div>
  </div>
</template>
