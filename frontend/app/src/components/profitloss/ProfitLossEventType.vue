<script setup lang="ts">
import { useHistoryEventMappings } from '@/composables/history/events/mapping';
import { useRefMap } from '@/composables/utils/useRefMap';

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
  <span class="flex items-center flex-col text-no-wrap gap-1">
    <RuiIcon
      v-if="icon"
      :name="icon"
      color="secondary"
    />
    {{ label }}
  </span>
</template>
