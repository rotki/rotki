<script lang="ts" setup>
import TransactionQueryStatusCurrent
  from '@/components/history/events/tx/query-status/TransactionQueryStatusCurrent.vue';
import TransactionQueryStatusDetails
  from '@/components/history/events/tx/query-status/TransactionQueryStatusDetails.vue';
import TransactionQueryStatusSteps from '@/components/history/events/tx/query-status/TransactionQueryStatusSteps.vue';
import type { EvmTransactionQueryData } from '@/types/websocket-messages';
import type { Blockchain } from '@rotki/common';

const props = withDefaults(defineProps<{
  onlyChains?: Blockchain[];
  transactions?: EvmTransactionQueryData[];
}>(), {
  onlyChains: () => [],
  transactions: () => [],
});

const { t } = useI18n();

const { isMdAndUp } = useBreakpoint();
const { transactions } = toRefs(props);

const wrapperComponentStyle = 'height: 300px';
const itemHeight = computed<number>(() => {
  if (get(isMdAndUp)) {
    return 60;
  }
  else {
    return 220;
  }
});

const itemStyle = computed(() => ({
  height: `${get(itemHeight)}px`,
}));

const { containerProps, list, wrapperProps } = useVirtualList(transactions, {
  itemHeight: get(itemHeight),
});
</script>

<template>
  <div>
    <h6 class="text-body-1 font-medium">
      {{ t('transactions.query_status.title') }}
    </h6>

    <TransactionQueryStatusCurrent
      :only-chains="onlyChains"
      class="text-subtitle-2 text-rui-text-secondary my-2"
    />

    <div
      v-bind="containerProps"
      :class="$style['scroll-container']"
      :style="wrapperComponentStyle"
    >
      <div v-bind="wrapperProps">
        <div
          v-for="item in list"
          :key="item.index"
          :style="itemStyle"
          class="py-1"
        >
          <TransactionQueryStatusDetails :item="item.data" />
          <TransactionQueryStatusSteps :item="item.data" />
        </div>
      </div>
    </div>
  </div>
</template>

<style module lang="scss">
.scroll-container::-webkit-scrollbar-thumb {
  min-height: 30px;
}
</style>
