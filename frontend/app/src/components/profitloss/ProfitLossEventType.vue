<script setup lang="ts">
const props = defineProps<{
  type: string;
}>();

const { getAccountingEventTypeData } = useHistoryEventMappings();

const { type } = toRefs(props);
const data = getAccountingEventTypeData(type);
const icon = useRefMap(data, ({ icon }) => icon);
const label = useRefMap(data, ({ label }) => label);
</script>

<template>
  <span class="d-flex align-center" :class="'flex-column'">
    <span>
      <VIcon color="accent"> {{ icon }} </VIcon>
    </span>
    <span class="mt-2 text-no-wrap">
      {{ label }}
    </span>
  </span>
</template>
