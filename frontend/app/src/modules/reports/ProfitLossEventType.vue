<script setup lang="ts">
import { useHistoryEventMappings } from '@/modules/history/events/mapping/use-history-event-mappings';

const { type } = defineProps<{
  type: string;
}>();

const { getAccountingEventTypeData } = useHistoryEventMappings();

const data = getAccountingEventTypeData(() => type);
</script>

<template>
  <span class="flex items-center flex-col text-no-wrap gap-1">
    <RuiIcon
      v-if="data?.icon"
      :name="data.icon"
      color="secondary"
    />
    {{ data?.label }}
  </span>
</template>
