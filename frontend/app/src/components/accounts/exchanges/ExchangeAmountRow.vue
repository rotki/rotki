<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { type SupportedExchange } from '@/types/exchanges';

const props = defineProps<{
  balance: BigNumber;
  exchange: SupportedExchange;
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
  <div class="flex flex-row">
    <div class="ml-2 mr-6">
      <LocationDisplay
        v-if="exchange"
        :identifier="exchange"
        size="48px"
        icon
      />
    </div>
    <div class="flex flex-col my-3">
      <span class="text-h6">
        {{ name }}
      </span>
      <span class="secondary--text text--lighten-5">
        <AmountDisplay
          show-currency="symbol"
          fiat-currency="USD"
          :value="balance"
        />
      </span>
    </div>
  </div>
</template>
