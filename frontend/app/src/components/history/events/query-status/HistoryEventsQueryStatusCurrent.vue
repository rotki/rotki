<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    locations?: string[];
  }>(),
  {
    locations: () => []
  }
);

const { locations } = toRefs(props);

const { t } = useI18n();

const { queryingLength, length, isAllFinished } =
  useEventsQueryStatus(locations);
</script>

<template>
  <query-status-current :finished="isAllFinished">
    <template #finished>
      {{ t('transactions.query_status_events.done_group', { length }) }}
    </template>

    <template #running>
      {{
        t('transactions.query_status_events.group', {
          length: queryingLength
        })
      }}
    </template>
  </query-status-current>
</template>
