<script setup lang="ts">
import { useEventsQueryStatus } from '@/composables/history/events/query-status/events-query-status';
import HistoryQueryStatusCurrent from '@/components/history/events/HistoryQueryStatusCurrent.vue';

const props = withDefaults(
  defineProps<{
    locations?: string[];
  }>(),
  {
    locations: () => [],
  },
);

const { locations } = toRefs(props);

const { t } = useI18n();

const { isAllFinished, length, queryingLength } = useEventsQueryStatus(locations);
</script>

<template>
  <HistoryQueryStatusCurrent :finished="isAllFinished">
    <template #finished>
      {{ t('transactions.query_status_events.done_group', length) }}
    </template>

    <template #running>
      {{ t('transactions.query_status_events.group', queryingLength) }}
    </template>
  </HistoryQueryStatusCurrent>
</template>
