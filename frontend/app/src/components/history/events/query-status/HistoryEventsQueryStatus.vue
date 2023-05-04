<script setup lang="ts">
const props = withDefaults(
  defineProps<{
    colspan: number;
    locations?: string[];
  }>(),
  {
    locations: () => []
  }
);

const { locations } = toRefs(props);

const {
  sortedQueryStatus,
  getKey,
  isQueryFinished,
  isAllFinished,
  resetQueryStatus
} = useEventsQueryStatus(locations);
</script>

<template>
  <query-status-bar
    :colspan="colspan"
    :items="sortedQueryStatus"
    :finished="isAllFinished"
    :get-key="getKey"
    :is-item-finished="isQueryFinished"
    @reset="resetQueryStatus()"
  >
    <template #current>
      <history-events-query-status-current :locations="locations" />
    </template>

    <template #item="{ item }">
      <location-icon icon no-padding :item="item.location" size="20px" />
      <history-events-query-status-line :item="item" class="ms-2" />
    </template>

    <template #dialog>
      <history-events-query-status-dialog :locations="locations" />
    </template>
  </query-status-bar>
</template>
