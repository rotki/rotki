<template>
  <div class="d-flex flex-row">
    <div class="ml-2 mr-6">
      <location-display :identifier="exchange" size="48px" icon />
    </div>
    <div class="d-flex flex-column my-3">
      <span class="text-h6">
        {{ exchangeName(exchange) }}
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

<script lang="ts">
import { BigNumber } from '@rotki/common';
import { defineComponent, PropType } from '@vue/composition-api';
import { exchangeName } from '@/components/history/consts';
import { SupportedExchange } from '@/types/exchanges';

export default defineComponent({
  name: 'ExchangeAmountRow',
  props: {
    balance: { required: true, type: BigNumber },
    exchange: { required: true, type: String as PropType<SupportedExchange> }
  },
  setup() {
    return {
      exchangeName
    };
  }
});
</script>
