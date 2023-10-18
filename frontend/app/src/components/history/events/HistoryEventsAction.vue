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
        <RuiButton variant="text" icon size="sm" class="!p-2" v-on="on">
          <RuiIcon name="more-2-fill" size="20" />
        </RuiButton>
      </template>
      <VList>
        <VListItem link class="gap-4" @click="addEvent(event)">
          <RuiIcon class="text-rui-text-secondary" name="add-line" />
          <VListItemContent>
            {{ t('transactions.actions.add_event_here') }}
          </VListItemContent>
        </VListItem>
        <VListItem link class="gap-4" @click="toggleIgnore(event)">
          <RuiIcon
            class="text-rui-text-secondary"
            :name="event.ignoredInAccounting ? 'eye-line' : 'eye-off-line'"
          />
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
            class="gap-4"
            @click="redecode(toEvmChainAndTxHash(evmEvent))"
          >
            <RuiIcon class="text-rui-text-secondary" name="restart-line" />
            <VListItemContent>
              {{ t('transactions.actions.redecode_events') }}
            </VListItemContent>
          </VListItem>
          <VListItem
            link
            :disabled="loading"
            class="gap-4"
            @click="resetEvent(evmEvent)"
          >
            <RuiIcon class="text-rui-text-secondary" name="file-edit-line" />

            <VListItemContent>
              {{ t('transactions.actions.reset_customized_events') }}
            </VListItemContent>
          </VListItem>
        </template>
      </VList>
    </VMenu>
  </div>
</template>
