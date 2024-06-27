<script setup lang="ts">
import type {
  EvmTransactionQueryData,
  EvmUnDecodedTransactionsData,
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
    decodingStatus: EvmUnDecodedTransactionsData[];
    decoding: boolean;
    currentAction: 'decode' | 'query';
  }>(),
  {
    onlyChains: () => [],
    locations: () => [],
    includeEvmEvents: false,
    includeOnlineEvents: false,
    loading: false,
  },
);

const emit = defineEmits<{
  (e: 'show-decode-details'): void;
  (e: 'update:current-action', value: 'decode' | 'query'): void;
}>();
const { onlyChains, locations, currentAction } = toRefs(props);
const { t } = useI18n();

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

const { resetUndecodedTransactionsStatus } = useHistoryStore();

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
  emit('update:current-action', 'query');
}
</script>

<template>
  <HistoryQueryStatusBar
    v-if="loading || decoding || items.length > 0"
    :colspan="colspan"
    :finished="isQuery ? !loading : !decoding"
    @reset="resetQueryStatus()"
  >
    <template #current>
      <HistoryQueryStatusCurrent
        v-if="isQuery"
        :finished="!loading"
      />
      <EventsDecodingStatusCurrent
        v-else
        :finished="!decoding"
      />
    </template>

    <template #dialog>
      <HistoryQueryStatusDialog
        v-if="isQuery"
        :only-chains="onlyChains"
        :locations="locations"
        :events="events"
        :transactions="transactions"
        :decoding-status="decodingStatus"
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
            @click="emit('show-decode-details')"
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
