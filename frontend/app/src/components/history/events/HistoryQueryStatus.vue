<script setup lang="ts">
import { TaskType } from '@/types/task-type';
import type {
  EvmTransactionQueryData,
  HistoryEventsQueryData,
} from '@/types/websocket-messages';
import type { Blockchain } from '@rotki/common';

const props = withDefaults(defineProps<{
  colspan: number;
  loading: boolean;
  onlyChains?: Blockchain[];
  locations?: string[];
  decoding: boolean;
}>(), {
  onlyChains: () => [],
  locations: () => [],
  loading: false,
});

const emit = defineEmits<{
  'show:dialog': [type: 'decode' | 'protocol-refresh'];
}>();

const currentAction = defineModel<'decode' | 'query'>('currentAction', { required: true });

const { onlyChains, locations } = toRefs(props);

const { t } = useI18n();

const { resetUndecodedTransactionsStatus } = useHistoryStore();
const { receivingProtocolCacheStatus, protocolCacheStatus } = storeToRefs(useHistoryStore());
const { decodingStatus } = storeToRefs(useHistoryStore());

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
const { isTaskRunning } = useTaskStore();

const refreshProtocolCacheTaskRunning = isTaskRunning(TaskType.REFRESH_GENERAL_CACHE);
const items = computed(() => [...get(transactions), ...get(events)]);
const isQuery = computed(() => get(currentAction) === 'query');

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
  resetUndecodedTransactionsStatus();
  set(currentAction, 'query');
}
</script>

<template>
  <HistoryQueryStatusBar
    v-if="loading || decoding || receivingProtocolCacheStatus || items.length > 0"
    :colspan="colspan"
    :finished="isQuery ? !loading : !receivingProtocolCacheStatus && !decoding"
    @reset="resetQueryStatus()"
  >
    <template #current>
      <EventsCacheRefreshStatusCurrent v-if="refreshProtocolCacheTaskRunning" />
      <HistoryQueryStatusCurrent
        v-else-if="isQuery"
        :finished="!loading"
      />
      <EventsDecodingStatusCurrent
        v-else
        :finished="!decoding"
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
              <RuiIcon name="information-line" />
            </template>
          </RuiButton>
        </template>
        {{ t('common.details') }}
      </RuiTooltip>
    </template>
  </HistoryQueryStatusBar>
</template>
