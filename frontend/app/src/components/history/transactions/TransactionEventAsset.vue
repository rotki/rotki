<template>
  <div>
    <div class="py-2 d-flex align-center">
      <div class="mr-2">
        <asset-icon size="32px" :identifier="event.asset" />
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
        {{ getAssetSymbol(event.asset) }}
      </div>
    </div>
  </div>
</template>
<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs,
  unref
} from '@vue/composition-api';
import { setupAssetInfoRetrieval } from '@/composables/balances';
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
    const { getAssetSymbol } = setupAssetInfoRetrieval();

    const showBalance = computed<boolean>(() => {
      const type = getEventType(unref(event));

      return type !== TransactionEventType.APPROVAL;
    });

    return {
      showBalance,
      getAssetSymbol
    };
  }
});
</script>
