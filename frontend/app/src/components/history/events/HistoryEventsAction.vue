<script setup lang="ts">
import {
  type EvmChainAndTxHash,
  type EvmHistoryEvent,
  type HistoryEventEntry
} from '@/types/history/events';
import { toEvmChainAndTxHash } from '@/utils/history';

const props = defineProps<{
  event: HistoryEventEntry;
  loading: boolean;
}>();

const emit = defineEmits<{
  (e: 'add-event', event: HistoryEventEntry): void;
  (e: 'toggle-ignore', event: HistoryEventEntry): void;
  (e: 'redecode', data: EvmChainAndTxHash): void;
  (e: 'reset', event: EvmHistoryEvent): void;
}>();

const { event } = toRefs(props);

const evmEvent = isEvmEventRef(event);

const { t } = useI18n();

const addEvent = (event: HistoryEventEntry) => emit('add-event', event);
const toggleIgnore = (event: HistoryEventEntry) => emit('toggle-ignore', event);
const redecode = (data: EvmChainAndTxHash) => emit('redecode', data);
const resetEvent = (event: EvmHistoryEvent) => emit('reset', event);
</script>

<template>
  <div class="flex items-center">
    <VMenu
      transition="slide-y-transition"
      max-width="250px"
      min-width="200px"
      offset-y
    >
      <template #activator="{ on }">
        <VBtn class="ml-1" icon v-on="on">
          <VIcon>mdi-dots-vertical</VIcon>
        </VBtn>
      </template>
      <VList>
        <VListItem link @click="addEvent(event)">
          <VListItemIcon class="mr-4">
            <VIcon>mdi-plus</VIcon>
          </VListItemIcon>
          <VListItemContent>
            {{ t('transactions.actions.add_event_here') }}
          </VListItemContent>
        </VListItem>
        <VListItem link @click="toggleIgnore(event)">
          <VListItemIcon class="mr-4">
            <VIcon v-if="event.ignoredInAccounting"> mdi-eye </VIcon>
            <VIcon v-else> mdi-eye-off</VIcon>
          </VListItemIcon>
          <VListItemContent>
            {{
              event.ignoredInAccounting
                ? t('transactions.unignore')
                : t('transactions.ignore')
            }}
          </VListItemContent>
        </VListItem>
        <template v-if="evmEvent">
          <VListItem
            link
            :disabled="loading"
            @click="redecode(toEvmChainAndTxHash(evmEvent))"
          >
            <VListItemIcon class="mr-4">
              <VIcon>mdi-database-refresh</VIcon>
            </VListItemIcon>
            <VListItemContent>
              {{ t('transactions.actions.redecode_events') }}
            </VListItemContent>
          </VListItem>
          <VListItem link :disabled="loading" @click="resetEvent(evmEvent)">
            <VListItemIcon class="mr-4">
              <VIcon>mdi-file-restore</VIcon>
            </VListItemIcon>
            <VListItemContent>
              {{ t('transactions.actions.reset_customized_events') }}
            </VListItemContent>
          </VListItem>
        </template>
      </VList>
    </VMenu>
  </div>
</template>
