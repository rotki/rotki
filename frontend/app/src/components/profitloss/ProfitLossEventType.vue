<script setup lang="ts">
import { useHistoryEventMappings } from '@/composables/history/events/mapping';

const { getAccountingEventTypeData } = useHistoryEventMappings();

const props = defineProps<{
  type: string;
}>();

const { type } = toRefs(props);
const data = getAccountingEventTypeData(type);
const icon = useRefMap(data, ({ icon }) => icon);
const label = useRefMap(data, ({ label }) => label);
</script>

<template>
  <span class="d-flex align-center" :class="'flex-column'">
    <span>
      <v-icon color="accent"> {{ icon }} </v-icon>
    </span>
    <span class="mt-2 text-no-wrap">
      {{ label }}
    </span>
  </span>
</template>
