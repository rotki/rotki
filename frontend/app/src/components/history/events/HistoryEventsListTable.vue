<script setup lang="ts">
import type { HistoryEventDeletePayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { HistoryEventEntry } from '@/types/history/events';
import HistoryEventsListItem from '@/components/history/events/HistoryEventsListItem.vue';
import HistoryEventsListSwap from '@/components/history/events/HistoryEventsListSwap.vue';
import { groupSwaps } from '@/modules/history/events/utils';

interface HistoryEventsListTableProps {
  events: HistoryEventEntry[];
  eventGroup: HistoryEventEntry;
  loading: boolean;
  total: number;
  highlightedIdentifiers?: string[];
}

const props = defineProps<HistoryEventsListTableProps>();

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: HistoryEventDeletePayload];
  'show:missing-rule-action': [data: HistoryEventEditData];
}>();

const { t } = useI18n();

const items = computed(() => groupSwaps(props.events));
</script>

<template>
  <div>
    <template v-if="total > 0">
      <template v-for="(item, index) in items">
        <HistoryEventsListItem
          v-if="item.type === 'evm'"
          :key="item.event.identifier"
          class="flex-1"
          :item="item.event"
          :index="index"
          :events="events"
          :event-group="eventGroup"
          :is-last="index === events.length - 1"
          :is-highlighted="highlightedIdentifiers?.includes(item.event.identifier.toString())"
          @edit-event="emit('edit-event', $event)"
          @delete-event="emit('delete-event', $event)"
          @show:missing-rule-action="emit('show:missing-rule-action', $event)"
        />

        <HistoryEventsListSwap
          v-else
          :key="`swap-${index}`"
          :events="item.events"
          :highlighted-identifiers="highlightedIdentifiers"
          @edit-event="emit('edit-event', $event)"
          @delete-event="emit('delete-event', $event)"
          @show:missing-rule-action="emit('show:missing-rule-action', $event)"
        />
      </template>
    </template>

    <template v-else>
      <div v-if="loading">
        {{ t('transactions.events.loading') }}
      </div>
      <div v-else>
        {{ t('transactions.events.no_data') }}
      </div>
    </template>
  </div>
</template>
