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

<script lang="ts">
import { BigNumber } from '@rotki/common';
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import { exchangeName } from '@/components/history/consts';
import { SupportedExchange } from '@/types/exchanges';

export default defineComponent({
  name: 'ExchangeAmountRow',
  props: {
    balance: { required: true, type: BigNumber },
    exchange: { required: true, type: String as PropType<SupportedExchange> }
  },
  setup(props) {
    const { exchange } = toRefs(props);

    const name = computed<string>(() => {
      if (!get(exchange)) return '';
      return exchangeName(get(exchange));
    });

    return {
      name
    };
  }
});
</script>
