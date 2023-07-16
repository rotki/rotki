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
  <QueryStatusBar
    :colspan="colspan"
    :items="sortedQueryStatus"
    :finished="isAllFinished"
    :get-key="getKey"
    :is-item-finished="isQueryFinished"
    @reset="resetQueryStatus()"
  >
    <template #current>
      <HistoryEventsQueryStatusCurrent :locations="locations" />
    </template>

    <template #item="{ item }">
      <LocationIcon icon no-padding :item="item.location" size="20px" />
      <HistoryEventsQueryStatusLine :item="item" class="ms-2" />
    </template>

    <template #dialog>
      <HistoryEventsQueryStatusDialog :locations="locations" />
    </template>
  </QueryStatusBar>
</template>
