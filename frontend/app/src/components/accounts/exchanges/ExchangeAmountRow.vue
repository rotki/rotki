<template>
  <div class="d-flex flex-row">
    <div class="ml-2 mr-6">
      <location-display
        v-if="exchange"
        :identifier="exchange"
        size="48px"
        icon
      />
    </div>
    <div class="d-flex flex-column my-3">
      <span class="text-h6">
        {{ name }}
      </span>
      <span class="secondary--text text--lighten-5">
        <amount-display
          show-currency="symbol"
          fiat-currency="USD"
          :value="balance"
        />
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import { PropType } from 'vue';
import { SupportedExchange } from '@/types/exchanges';
import { useTradeLocations } from '@/types/trades';

const props = defineProps({
  balance: { required: true, type: BigNumber },
  exchange: { required: true, type: String as PropType<SupportedExchange> }
});

const { exchange } = toRefs(props);
const { exchangeName } = useTradeLocations();

const name = computed<string>(() => {
  if (!get(exchange)) return '';
  return exchangeName(exchange);
});
</script>
