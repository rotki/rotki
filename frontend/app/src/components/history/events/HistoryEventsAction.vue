<script setup lang="ts">
import type {
  EvmChainAndTxHash,
  PullEventPayload,
} from '@/types/history/events';
import type {
  EthBlockEvent,
  EvmHistoryEvent,
  EvmSwapEvent,
  HistoryEvent,
  HistoryEventEntry,
  StandaloneEditableEvents,
} from '@/types/history/events/schemas';
import { useSupportedChains } from '@/composables/info/chains';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import { isEvmSwapEvent, isGroupEditableHistoryEvent } from '@/modules/history/management/forms/form-guards';
import { toEvmChainAndTxHash } from '@/utils/history';
import { isEthBlockEvent, isEthBlockEventRef, isEvmEvent, isOnlineHistoryEvent } from '@/utils/history/events';

interface EventInfo { txHash: string; location: string }

const props = defineProps<{
  event: HistoryEventEntry;
  loading: boolean;
}>();

const emit = defineEmits<{
  'add-event': [event: StandaloneEditableEvents];
  'toggle-ignore': [event: HistoryEventEntry];
  'redecode': [event: PullEventPayload];
  'delete-tx': [data: EvmChainAndTxHash];
}>();

const {
  ethBlockEventsDecoding,
  evmEventsDecoding,
} = useHistoryEventsStatus();

const { event } = toRefs(props);

const evmEvent = computed<EvmHistoryEvent | EvmSwapEvent | undefined>(() => {
  const currentEvent = get(event);
  if (isEvmSwapEvent(currentEvent) || isEvmEvent(currentEvent)) {
    return currentEvent;
  }
  return undefined;
});

const eventWithTxHash = computed<{ location: string; txHash: string } | undefined>(() => {
  const currentEvent = get(event);
  if (get(evmEvent)) {
    return get(evmEvent);
  }
  if (isOnlineHistoryEvent(currentEvent) && 'txHash' in currentEvent && currentEvent.txHash) {
    return {
      location: currentEvent.location,
      txHash: currentEvent.txHash,
    };
  }

  return undefined;
});

const blockEvent = isEthBlockEventRef(event);

const { getChain } = useSupportedChains();

const { t } = useI18n({ useScope: 'global' });

function addEvent(event: HistoryEvent) {
  if (isGroupEditableHistoryEvent(event)) {
    return;
  }
  emit('add-event', event);
}
const toggleIgnore = (event: HistoryEventEntry) => emit('toggle-ignore', event);

function redecode(event: EthBlockEvent | EvmHistoryEvent | EvmSwapEvent) {
  if (isEthBlockEvent(event)) {
    emit('redecode', {
      data: [event.blockNumber],
      type: event.entryType,
    });
  }
  else {
    emit('redecode', {
      data: toEvmChainAndTxHash({ location: event.location, txHash: event.txHash }),
      type: event.entryType,
    });
  }
}

function deleteTxAndEvents({ location, txHash }: EventInfo) {
  return emit('delete-tx', { evmChain: getChain(location), txHash });
}

function hideAddAction(item: HistoryEvent): boolean {
  return isGroupEditableHistoryEvent(item);
}
</script>

<template>
  <div class="flex items-center">
    <RuiMenu
      menu-class="max-w-[15rem]"
      :popper="{ placement: 'bottom-end' }"
      close-on-content-click
    >
      <template #activator="{ attrs }">
        <RuiButton
          variant="text"
          icon
          size="sm"
          class="!p-2"
          v-bind="attrs"
        >
          <RuiIcon
            name="lu-ellipsis-vertical"
            size="20"
          />
        </RuiButton>
      </template>
      <div class="py-2">
        <RuiButton
          v-if="!hideAddAction(event)"
          variant="list"
          @click="addEvent(event)"
        >
          <template #prepend>
            <RuiIcon name="lu-plus" />
          </template>
          {{ t('transactions.actions.add_event_here') }}
        </RuiButton>
        <RuiButton
          variant="list"
          @click="toggleIgnore(event)"
        >
          <template #prepend>
            <RuiIcon :name="event.ignoredInAccounting ? 'lu-eye' : 'lu-eye-off'" />
          </template>
          {{ event.ignoredInAccounting ? t('transactions.unignore') : t('transactions.ignore') }}
        </RuiButton>
        <template v-if="blockEvent">
          <RuiButton
            variant="list"
            :disabled="loading || ethBlockEventsDecoding"
            @click="redecode(blockEvent)"
          >
            <template #prepend>
              <RuiIcon name="lu-rotate-ccw" />
            </template>
            {{ t('transactions.actions.redecode_events') }}
          </RuiButton>
        </template>
        <template v-else-if="evmEvent">
          <RuiButton
            variant="list"
            :disabled="loading || evmEventsDecoding"
            @click="redecode(evmEvent)"
          >
            <template #prepend>
              <RuiIcon name="lu-rotate-ccw" />
            </template>
            {{ t('transactions.actions.redecode_events') }}
          </RuiButton>
        </template>
        <RuiButton
          v-if="eventWithTxHash"
          variant="list"
          color="error"
          :disabled="loading"
          @click="deleteTxAndEvents(eventWithTxHash)"
        >
          <template #prepend>
            <RuiIcon name="lu-trash-2" />
          </template>
          {{ t('transactions.actions.delete_transaction') }}
        </RuiButton>
      </div>
    </RuiMenu>
  </div>
</template>
