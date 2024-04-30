<script setup lang="ts">
import { toEvmChainAndTxHash } from '@/utils/history';
import type {
  EvmChainAndTxHash,
  EvmHistoryEvent,
  HistoryEventEntry,
} from '@/types/history/events';

const props = defineProps<{
  event: HistoryEventEntry;
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: 'add-event', event: HistoryEventEntry): void;
  (e: 'toggle-ignore', event: HistoryEventEntry): void;
  (e: 'redecode', data: EvmChainAndTxHash): void;
  (e: 'reset', event: EvmHistoryEvent): void;
  (e: 'delete-tx', data: EvmChainAndTxHash): void;
}>();

const { event } = toRefs(props);

const evmEvent = isEvmEventRef(event);
const { getChain } = useSupportedChains();

const { t } = useI18n();

const addEvent = (event: HistoryEventEntry) => emit('add-event', event);
const toggleIgnore = (event: HistoryEventEntry) => emit('toggle-ignore', event);
const redecode = (data: EvmChainAndTxHash) => emit('redecode', data);
const resetEvent = (event: EvmHistoryEvent) => emit('reset', event);
const deleteTxAndEvents = ({ txHash, location }: EvmHistoryEvent) => emit('delete-tx', { txHash, evmChain: getChain(location) });
</script>

<template>
  <div class="flex items-center">
    <RuiMenu
      menu-class="max-w-[15rem]"
      :popper="{ placement: 'bottom-end' }"
      close-on-content-click
    >
      <template #activator="{ on }">
        <RuiButton
          variant="text"
          icon
          size="sm"
          class="!p-2"
          v-on="on"
        >
          <RuiIcon
            name="more-2-fill"
            size="20"
          />
        </RuiButton>
      </template>
      <div class="py-2">
        <RuiButton
          variant="list"
          @click="addEvent(event)"
        >
          <template #prepend>
            <RuiIcon name="add-line" />
          </template>
          {{ t('transactions.actions.add_event_here') }}
        </RuiButton>
        <RuiButton
          variant="list"
          @click="toggleIgnore(event)"
        >
          <template #prepend>
            <RuiIcon :name="event.ignoredInAccounting ? 'eye-line' : 'eye-off-line'" />
          </template>
          {{
            event.ignoredInAccounting
              ? t('transactions.unignore')
              : t('transactions.ignore')
          }}
        </RuiButton>
        <template v-if="evmEvent">
          <RuiButton
            variant="list"
            :disabled="loading"
            @click="redecode(toEvmChainAndTxHash(evmEvent))"
          >
            <template #prepend>
              <RuiIcon name="restart-line" />
            </template>
            {{ t('transactions.actions.redecode_events') }}
          </RuiButton>
          <RuiButton
            variant="list"
            :disabled="loading"
            @click="resetEvent(evmEvent)"
          >
            <template #prepend>
              <RuiIcon name="file-edit-line" />
            </template>
            {{ t('transactions.actions.reset_customized_events') }}
          </RuiButton>
          <RuiButton
            variant="list"
            color="error"
            :disabled="loading"
            @click="deleteTxAndEvents(evmEvent)"
          >
            <template #prepend>
              <RuiIcon name="delete-bin-line" />
            </template>
            {{ t('transactions.actions.delete_transaction') }}
          </RuiButton>
        </template>
      </div>
    </RuiMenu>
  </div>
</template>
