<script setup lang="ts">
import type {
  EvmTransactionQueryData,
  HistoryEventsQueryData,
} from '@/types/websocket-messages';
import type { Blockchain } from '@rotki/common/lib/blockchain';

const props = withDefaults(
  defineProps<{
    colspan: number;
    loading: boolean;
    includeEvmEvents: boolean;
    includeOnlineEvents: boolean;
    onlyChains?: Blockchain[];
    locations?: string[];
  }>(),
  {
    onlyChains: () => [],
    locations: () => [],
    includeEvmEvents: false,
    includeOnlineEvents: false,
    loading: false,
  },
);

const { onlyChains, locations } = toRefs(props);

const {
  sortedQueryStatus: transactions,
  getKey: getTransactionKey,
  isQueryFinished: isTransactionQueryFinished,
  resetQueryStatus: resetTransactionsQueryStatus,
} = useTransactionQueryStatus(onlyChains);

const {
  sortedQueryStatus: events,
  getKey: getEventKey,
  isQueryFinished: isEventQueryFinished,
  resetQueryStatus: resetEventsQueryStatus,
} = useEventsQueryStatus(locations);

const items = computed(() => [...get(transactions), ...get(events)]);

function getItemKey(item: EvmTransactionQueryData | HistoryEventsQueryData) {
  if ('eventType' in item)
    return getEventKey(item);

  return getTransactionKey(item);
}

function isItemQueryFinished(item: EvmTransactionQueryData | HistoryEventsQueryData) {
  if ('eventType' in item)
    return isEventQueryFinished(item);

  return isTransactionQueryFinished(item);
}

function resetQueryStatus() {
  resetTransactionsQueryStatus();
  resetEventsQueryStatus();
}
</script>

<template>
  <HistoryQueryStatusBar
    :colspan="colspan"
    :total="items.length"
    :finished="!loading"
    @reset="resetQueryStatus()"
  >
    <template #current>
      <HistoryQueryStatusCurrent :finished="!loading" />
    </template>

    <template #dialog>
      <HistoryQueryStatusDialog
        :only-chains="onlyChains"
        :locations="locations"
        :events="events"
        :transactions="transactions"
        :get-key="getItemKey"
        :is-item-finished="isItemQueryFinished"
      />
    </template>
  </HistoryQueryStatusBar>
</template>
