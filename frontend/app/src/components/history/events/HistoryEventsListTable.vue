<script setup lang="ts">
import type { HistoryEventDeletePayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { HistoryEventEntry, HistoryEventRow } from '@/types/history/events/schemas';
import HistoryEventsListItem from '@/components/history/events/HistoryEventsListItem.vue';
import HistoryEventsListSwap from '@/components/history/events/HistoryEventsListSwap.vue';
import { flatten } from 'es-toolkit';

interface HistoryEventsListTableProps {
  events: HistoryEventRow[];
  eventGroup: HistoryEventEntry;
  loading: boolean;
  total: number;
  highlightedIdentifiers?: string[];
}

defineProps<HistoryEventsListTableProps>();

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: HistoryEventDeletePayload];
  'show:missing-rule-action': [data: HistoryEventEditData];
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="@container">
    <template v-if="total > 0">
      <template v-for="(item, index) in events">
        <HistoryEventsListSwap
          v-if="Array.isArray(item)"
          :key="`swap-${index}`"
          :events="item"
          :highlighted-identifiers="highlightedIdentifiers"
          @edit-event="emit('edit-event', $event)"
          @delete-event="emit('delete-event', $event)"
          @show:missing-rule-action="emit('show:missing-rule-action', $event)"
        />
        <HistoryEventsListItem
          v-else
          :key="item.identifier"
          class="flex-1"
          :item="item"
          :index="index"
          :events="flatten(events)"
          :event-group="eventGroup"
          :is-last="index === events.length - 1"
          :is-highlighted="highlightedIdentifiers?.includes(item.identifier.toString())"
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
