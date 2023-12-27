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
      left
      offset-y
    >
      <template #activator="{ on }">
        <RuiButton variant="text" icon size="sm" class="!p-2" v-on="on">
          <RuiIcon name="more-2-fill" size="20" />
        </RuiButton>
      </template>
      <div class="py-2">
        <RuiButton variant="list" @click="addEvent(event)">
          <template #prepend>
            <RuiIcon class="text-rui-text-secondary" name="add-line" />
          </template>
          {{ t('transactions.actions.add_event_here') }}
        </RuiButton>
        <RuiButton variant="list" @click="toggleIgnore(event)">
          <template #prepend>
            <RuiIcon
              class="text-rui-text-secondary"
              :name="event.ignoredInAccounting ? 'eye-line' : 'eye-off-line'"
            />
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
              <RuiIcon class="text-rui-text-secondary" name="restart-line" />
            </template>
            {{ t('transactions.actions.redecode_events') }}
          </RuiButton>
          <RuiButton
            variant="list"
            :disabled="loading"
            @click="resetEvent(evmEvent)"
          >
            <template #prepend>
              <RuiIcon class="text-rui-text-secondary" name="file-edit-line" />
            </template>
            {{ t('transactions.actions.reset_customized_events') }}
          </RuiButton>
        </template>
      </div>
    </VMenu>
  </div>
</template>
