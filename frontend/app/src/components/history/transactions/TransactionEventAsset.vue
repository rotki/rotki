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
<script setup lang="ts">
import { PropType } from 'vue';
import { useAssetInfoRetrieval } from '@/store/assets/retrieval';
import { EthTransactionEventEntry } from '@/store/history/types';
import { TransactionEventType } from '@/types/transaction';
import { getEventType } from '@/utils/history';

const props = defineProps({
  event: {
    required: true,
    type: Object as PropType<EthTransactionEventEntry>
  }
});

const { event } = toRefs(props);
const { assetSymbol } = useAssetInfoRetrieval();

const showBalance = computed<boolean>(() => {
  return getEventType(get(event)) !== TransactionEventType.APPROVAL;
});

const eventAsset = computed(() => get(event).asset);
const symbol = assetSymbol(eventAsset);
</script>
