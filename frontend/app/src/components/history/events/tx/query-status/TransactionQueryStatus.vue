<script lang="ts" setup>
import type { TxQueryStatusData } from '@/store/history/query-status/tx-query-status';
import TransactionQueryStatusCurrent from './TransactionQueryStatusCurrent.vue';
import TransactionQueryStatusDetails from './TransactionQueryStatusDetails.vue';
import TransactionQueryStatusSteps from './TransactionQueryStatusSteps.vue';

const props = withDefaults(defineProps<{
  onlyChains?: string[];
  queryStatuses?: TxQueryStatusData[];
}>(), {
  onlyChains: () => [],
  queryStatuses: () => [],
});

const { t } = useI18n({ useScope: 'global' });

const { isMdAndUp } = useBreakpoint();
const { queryStatuses } = toRefs(props);

const wrapperComponentStyle = 'height: 300px';
const itemHeight = computed<number>(() => {
  if (get(isMdAndUp)) {
    return 60;
  }
  else {
    return 200;
  }
});

const itemStyle = computed(() => ({
  height: `${get(itemHeight)}px`,
}));

const { containerProps, list, wrapperProps } = useVirtualList(queryStatuses, {
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
      v-if="queryStatuses.length > 0"
      v-bind="containerProps"
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
          <TransactionQueryStatusSteps
            v-if="item.data.subtype !== 'bitcoin'"
            :item="item.data"
          />
        </div>
      </div>
    </div>
  </div>
</template>
