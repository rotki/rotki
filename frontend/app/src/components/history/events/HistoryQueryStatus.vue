<script setup lang="ts">
import type { TxQueryStatusData } from '@/store/history/query-status/tx-query-status';
import type {
  HistoryEventsQueryData,
} from '@/types/websocket-messages';
import EventsCacheRefreshStatusCurrent from '@/components/history/events/EventsCacheRefreshStatusCurrent.vue';
import EventsDecodingStatusCurrent from '@/components/history/events/EventsDecodingStatusCurrent.vue';
import HistoryQueryStatusBar from '@/components/history/events/HistoryQueryStatusBar.vue';
import HistoryQueryStatusCurrent from '@/components/history/events/HistoryQueryStatusCurrent.vue';
import HistoryQueryStatusDialog from '@/components/history/events/HistoryQueryStatusDialog.vue';
import { useEventsQueryStatus } from '@/composables/history/events/query-status/events-query-status';
import { useTransactionQueryStatus } from '@/composables/history/events/query-status/tx-query-status';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { useHistoryStore } from '@/store/history';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';

const currentAction = defineModel<'decode' | 'query'>('currentAction', { required: true });

const props = withDefaults(defineProps<{
  colspan: number;
  loading: boolean;
  onlyChains?: string[];
  locations?: string[];
}>(), {
  locations: () => [],
  onlyChains: () => [],
});

const emit = defineEmits<{
  'show:dialog': [type: 'decode' | 'protocol-refresh'];
}>();

const { loading, locations, onlyChains } = toRefs(props);

const { t } = useI18n({ useScope: 'global' });

const {
  anyEventsDecoding,
  ethBlockEventsDecoding,
} = useHistoryEventsStatus();

const { resetUndecodedTransactionsStatus } = useHistoryStore();
const { protocolCacheStatus, receivingProtocolCacheStatus } = storeToRefs(useHistoryStore());
const { decodingStatus } = storeToRefs(useHistoryStore());

const {
  getKey: getTransactionKey,
  isQueryFinished: isTransactionQueryFinished,
  resetQueryStatus: resetTransactionsQueryStatus,
  sortedQueryStatus: transactions,
} = useTransactionQueryStatus(onlyChains);

const {
  getKey: getEventKey,
  isQueryFinished: isEventQueryFinished,
  resetQueryStatus: resetEventsQueryStatus,
  sortedQueryStatus: events,
} = useEventsQueryStatus(locations);
const { useIsTaskRunning } = useTaskStore();

const refreshProtocolCacheTaskRunning = useIsTaskRunning(TaskType.REFRESH_GENERAL_CACHE);
const items = computed(() => [...get(transactions), ...get(events)]);
const isQuery = computed(() => get(currentAction) === 'query');

const show = computed(() => get(loading) || get(anyEventsDecoding) || get(receivingProtocolCacheStatus) || get(items).length > 0);
const showDebounced = refDebounced(show, 400);
const usedShow = logicOr(show, showDebounced);

function getItemKey(item: TxQueryStatusData | HistoryEventsQueryData) {
  if ('eventType' in item)
    return getEventKey(item);

  return getTransactionKey(item);
}

function isItemQueryFinished(item: TxQueryStatusData | HistoryEventsQueryData) {
  if ('eventType' in item)
    return isEventQueryFinished(item);

  return isTransactionQueryFinished(item);
}

function resetQueryStatus() {
  resetTransactionsQueryStatus();
  resetEventsQueryStatus();
  resetUndecodedTransactionsStatus();
  set(currentAction, 'query');
}
</script>

<template>
  <HistoryQueryStatusBar
    v-if="usedShow"
    :colspan="colspan"
    :finished="isQuery ? !loading : !receivingProtocolCacheStatus && !anyEventsDecoding"
    @reset="resetQueryStatus()"
  >
    <template #current>
      <EventsCacheRefreshStatusCurrent v-if="refreshProtocolCacheTaskRunning" />
      <HistoryQueryStatusCurrent
        v-else-if="isQuery"
        :finished="!loading"
      />
      <HistoryQueryStatusCurrent v-else-if="ethBlockEventsDecoding">
        <template #running>
          {{ t('transactions.events_decoding.decoding.eth_block_events') }}
        </template>
      </HistoryQueryStatusCurrent>
      <EventsDecodingStatusCurrent
        v-else
        :finished="!anyEventsDecoding"
      />
    </template>

    <template #dialog>
      <HistoryQueryStatusDialog
        v-if="isQuery && !refreshProtocolCacheTaskRunning"
        :only-chains="onlyChains"
        :locations="locations"
        :events="events"
        :transactions="transactions"
        :decoding-status="decodingStatus"
        :loading="loading"
        :protocol-cache-status="protocolCacheStatus"
        :get-key="getItemKey"
        :is-item-finished="isItemQueryFinished"
      />

      <RuiTooltip
        v-else
        :popper="{ placement: 'top' }"
        :open-delay="400"
        class="ml-4"
      >
        <template #activator>
          <RuiButton
            variant="text"
            icon
            size="sm"
            class="!p-2"
            @click="emit('show:dialog', refreshProtocolCacheTaskRunning ? 'protocol-refresh' : 'decode')"
          >
            <template #append>
              <RuiIcon name="lu-info" />
            </template>
          </RuiButton>
        </template>
        {{ t('common.details') }}
      </RuiTooltip>
    </template>
  </HistoryQueryStatusBar>
</template>
