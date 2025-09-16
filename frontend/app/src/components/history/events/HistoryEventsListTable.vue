<script setup lang="ts">
import type { UseHistoryEventsSelectionModeReturn } from '@/modules/history/events/composables/use-selection-mode';
import type { HistoryEventDeletePayload } from '@/modules/history/events/types';
import type { HistoryEventEditData } from '@/modules/history/management/forms/form-types';
import type { HistoryEventEntry, HistoryEventRow } from '@/types/history/events/schemas';
import { flatten } from 'es-toolkit';
import HistoryEventsListItem from '@/components/history/events/HistoryEventsListItem.vue';
import HistoryEventsListSwap from '@/components/history/events/HistoryEventsListSwap.vue';

interface HistoryEventsListTableProps {
  allEvents: HistoryEventRow[];
  events: HistoryEventRow[];
  eventGroup: HistoryEventEntry;
  loading: boolean;
  total: number;
  highlightedIdentifiers?: string[];
  selection: UseHistoryEventsSelectionModeReturn;
}

const props = defineProps<HistoryEventsListTableProps>();

const emit = defineEmits<{
  'edit-event': [data: HistoryEventEditData];
  'delete-event': [data: HistoryEventDeletePayload];
  'show:missing-rule-action': [data: HistoryEventEditData];
  'refresh': [];
}>();

const { t } = useI18n({ useScope: 'global' });

function findAllEventsFromArrayItem(items: HistoryEventEntry[]): HistoryEventEntry[] | undefined {
  if (items.length === 0)
    return undefined;

  const firstId = items[0].identifier;

  const arrayOnly: HistoryEventEntry[][] = props.allEvents.filter(event => Array.isArray(event));
  return arrayOnly.find(event => event.map(item => item.identifier).includes(firstId));
}
</script>

<template>
  <div class="@container">
    <template v-if="total > 0">
      <template v-for="(item, index) in events">
        <HistoryEventsListSwap
          v-if="Array.isArray(item)"
          :key="`swap-${index}`"
          :events="item"
          :all-events="findAllEventsFromArrayItem(item) || item"
          :highlighted-identifiers="highlightedIdentifiers"
          :selection="selection"
          @edit-event="emit('edit-event', $event)"
          @delete-event="emit('delete-event', $event)"
          @show:missing-rule-action="emit('show:missing-rule-action', $event)"
          @refresh="emit('refresh')"
        />
        <HistoryEventsListItem
          v-else
          :key="item.identifier"
          class="flex-1"
          :item="item"
          :index="index"
          :events="flatten(allEvents)"
          :event-group="eventGroup"
          :is-last="index === events.length - 1"
          :is-highlighted="highlightedIdentifiers?.includes(item.identifier.toString())"
          :selection="selection"
          @edit-event="emit('edit-event', $event)"
          @delete-event="emit('delete-event', $event)"
          @show:missing-rule-action="emit('show:missing-rule-action', $event)"
          @refresh="emit('refresh')"
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
