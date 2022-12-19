<script setup lang="ts">
import { type PropType } from 'vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import { type EventType } from '@/types/defi/event-type';

const props = defineProps({
  eventType: { required: true, type: String as PropType<EventType> }
});
const { eventType } = toRefs(props);

const event = computed<string>(() => {
  return get(eventType) === 'comp' ? 'comp claimed' : get(eventType);
});
</script>

<template>
  <badge-display>
    {{ event }}
  </badge-display>
</template>
