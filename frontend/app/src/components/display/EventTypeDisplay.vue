<template>
  <badge-display>
    {{ event }}
  </badge-display>
</template>

<script setup lang="ts">
import { PropType } from 'vue';
import BadgeDisplay from '@/components/history/BadgeDisplay.vue';
import { EventType } from '@/types/defi/event-type';

const props = defineProps({
  eventType: { required: true, type: String as PropType<EventType> }
});
const { eventType } = toRefs(props);

const event = computed<string>(() => {
  return get(eventType) === 'comp' ? 'comp claimed' : get(eventType);
});
</script>
