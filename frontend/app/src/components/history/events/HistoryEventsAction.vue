<script setup lang="ts">
import type {
  LocationAndTxHash,
  PullEventPayload,
} from '@/types/history/events';
import type {
  EthBlockEvent,
  EvmHistoryEvent,
  EvmSwapEvent,
  HistoryEvent,
  HistoryEventEntry,
  SolanaEvent,
  SolanaSwapEvent,
  StandaloneEditableEvents,
} from '@/types/history/events/schemas';
import { useHistoryEventsStatus } from '@/modules/history/events/use-history-events-status';
import {
  type DecodableEventType,
  isEvmSwapEvent,
  isGroupEditableHistoryEvent,
} from '@/modules/history/management/forms/form-guards';
import { toLocationAndTxHash } from '@/utils/history';
import {
  isEthBlockEvent,
  isEthBlockEventRef,
  isEvmEvent,
  isOnlineHistoryEvent,
  isSolanaEvent,
  isSolanaSwapEvent,
} from '@/utils/history/events';

const props = defineProps<{
  event: HistoryEventEntry;
  loading: boolean;
}>();

const emit = defineEmits<{
  'add-event': [event: StandaloneEditableEvents];
  'toggle-ignore': [event: HistoryEventEntry];
  'redecode': [event: PullEventPayload];
  'delete-tx': [data: LocationAndTxHash];
}>();

const {
  ethBlockEventsDecoding,
  txEventsDecoding,
} = useHistoryEventsStatus();

const { event } = toRefs(props);

const evmEvent = computed<EvmHistoryEvent | EvmSwapEvent | undefined>(() => {
  const currentEvent = get(event);
  if (isEvmSwapEvent(currentEvent) || isEvmEvent(currentEvent)) {
    return currentEvent;
  }

  return undefined;
});

const solanaEvent = computed<SolanaEvent | SolanaSwapEvent | undefined>(() => {
  const currentEvent = get(event);
  if (isSolanaSwapEvent(currentEvent) || isSolanaEvent(currentEvent)) {
    return currentEvent;
  }

  return undefined;
});

const eventWithDecoding = computed<DecodableEventType | undefined>(() => get(evmEvent) || get(solanaEvent));

const eventWithTxHash = computed<{ location: string; txHash: string } | undefined>(() => {
  const currentEvent = get(event);
  const evm = get(evmEvent);
  const solana = get(solanaEvent);
  if (evm) {
    return evm;
  }

  if (solana) {
    return {
      location: solana.location,
      txHash: solana.signature,
    };
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

const { t } = useI18n({ useScope: 'global' });

function addEvent(event: HistoryEvent) {
  if (isGroupEditableHistoryEvent(event)) {
    return;
  }
  emit('add-event', event);
}
const toggleIgnore = (event: HistoryEventEntry) => emit('toggle-ignore', event);

function redecode(event: EthBlockEvent | DecodableEventType): void {
  if (isEthBlockEvent(event)) {
    emit('redecode', {
      data: [event.blockNumber],
      type: event.entryType,
    });
    return;
  }

  emit('redecode', {
    data: toLocationAndTxHash(event),
    type: event.entryType,
  });
}

function deleteTxAndEvents(params: LocationAndTxHash) {
  return emit('delete-tx', params);
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
        <template v-else-if="eventWithDecoding">
          <RuiButton
            variant="list"
            :disabled="loading || txEventsDecoding"
            @click="redecode(eventWithDecoding)"
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
