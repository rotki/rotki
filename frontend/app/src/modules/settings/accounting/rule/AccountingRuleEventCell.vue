<script setup lang="ts">
import HistoryEventTypeCombination from '@/modules/history/events/HistoryEventTypeCombination.vue';
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';

/** The event a rule applies to: the action it resolves to, with the type and subtype it is keyed on underneath. */
const { eventType, eventSubtype } = defineProps<{
  eventType: string;
  eventSubtype: string;
}>();

const { getEventTypeData, getHistoryEventSubTypeName, getHistoryEventTypeName } = useHistoryEventMappings();

const type = getEventTypeData(() => ({ eventSubtype, eventType }));
</script>

<template>
  <div class="flex items-center gap-3">
    <HistoryEventTypeCombination :type="type" />
    <div class="flex flex-col min-w-0">
      <span
        class="text-sm font-medium text-rui-text truncate"
        data-testid="accounting-rule-action"
      >
        {{ type.label }}
      </span>
      <span class="flex items-center gap-1.5 text-xs text-rui-text-secondary truncate">
        <span data-testid="accounting-rule-event-type">{{ getHistoryEventTypeName(eventType) }}</span>
        <span class="size-0.5 shrink-0 rounded-full bg-current" />
        <span data-testid="accounting-rule-event-subtype">{{ getHistoryEventSubTypeName(eventSubtype) }}</span>
      </span>
    </div>
  </div>
</template>
