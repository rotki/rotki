<script setup lang="ts" generic="T extends HistoryEventEntry = HistoryEventEntry">
import type { EvmChainAndTxHash, EvmHistoryEvent, HistoryEventEntry } from '@/types/history/events';
import { useSupportedChains } from '@/composables/info/chains';
import { useTaskStore } from '@/store/tasks';
import { TaskType } from '@/types/task-type';
import { toEvmChainAndTxHash } from '@/utils/history';
import { isEvmEventRef } from '@/utils/history/events';
import { HistoryEventEntryType } from '@rotki/common';

const props = defineProps<{
  event: T;
  loading: boolean;
}>();

const emit = defineEmits<{
  'add-event': [event: T];
  'toggle-ignore': [event: T];
  'redecode': [data: EvmChainAndTxHash];
  'delete-tx': [data: EvmChainAndTxHash];
}>();

const { useIsTaskRunning } = useTaskStore();
const eventTaskLoading = useIsTaskRunning(TaskType.TRANSACTIONS_DECODING);

const { event } = toRefs(props);

const evmEvent = isEvmEventRef(event);
const { getChain } = useSupportedChains();

const { t } = useI18n();

const addEvent = (event: T) => emit('add-event', event);
const toggleIgnore = (event: T) => emit('toggle-ignore', event);
const redecode = (data: EvmChainAndTxHash) => emit('redecode', data);

function deleteTxAndEvents({ location, txHash }: EvmHistoryEvent) {
  return emit('delete-tx', { evmChain: getChain(location), txHash });
}

function hideAddAction(item: T): boolean {
  const eventTypes: HistoryEventEntryType[] = [
    HistoryEventEntryType.ASSET_MOVEMENT_EVENT,
    HistoryEventEntryType.SWAP_EVENT,
  ];
  return eventTypes.includes(item.entryType);
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
        <template v-if="evmEvent">
          <RuiButton
            variant="list"
            :disabled="loading || eventTaskLoading"
            @click="redecode(toEvmChainAndTxHash(evmEvent))"
          >
            <template #prepend>
              <RuiIcon name="lu-rotate-ccw" />
            </template>
            {{ t('transactions.actions.redecode_events') }}
          </RuiButton>
          <RuiButton
            variant="list"
            color="error"
            :disabled="loading"
            @click="deleteTxAndEvents(evmEvent)"
          >
            <template #prepend>
              <RuiIcon name="lu-trash-2" />
            </template>
            {{ t('transactions.actions.delete_transaction') }}
          </RuiButton>
        </template>
      </div>
    </RuiMenu>
  </div>
</template>
