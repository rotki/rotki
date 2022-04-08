<template>
  <div>
    <div class="py-2 d-flex align-center">
      <div class="mr-2">
        <asset-link :asset="event.asset" icon>
          <asset-icon size="32px" :identifier="event.asset" />
        </asset-link>
      </div>
      <div v-if="showBalance">
        <div>
          <amount-display :value="event.balance.amount" :asset="event.asset" />
        </div>
        <div>
          <amount-display
            :value="event.balance.usdValue"
            fiat-currency="USD"
            class="grey--text"
          />
        </div>
      </div>
      <div v-else>
        {{ symbol }}
      </div>
    </div>
  </div>
</template>
<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import { useAssetInfoRetrieval } from '@/store/assets';
import { EthTransactionEventEntry } from '@/store/history/types';
import { TransactionEventType } from '@/types/transaction';
import { getEventType } from '@/utils/history';

export default defineComponent({
  name: 'TransactionEventAsset',
  props: {
    event: {
      required: true,
      type: Object as PropType<EthTransactionEventEntry>
    }
  },

  setup(props) {
    const { event } = toRefs(props);

    const { assetSymbol } = useAssetInfoRetrieval();

    const showBalance = computed<boolean>(() => {
      const type = getEventType(get(event));

      return type !== TransactionEventType.APPROVAL;
    });

    const symbol = computed<string>(() => {
      return get(assetSymbol(get(event).asset));
    });

    return {
      showBalance,
      symbol
    };
  }
});
</script>
