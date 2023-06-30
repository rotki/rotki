<script setup lang="ts">
const props = defineProps<{ eventType: string }>();
const { eventType } = toRefs(props);

const event = computed<string>(() =>
  get(eventType) === 'comp' ? 'comp claimed' : get(eventType)
);
</script>

<template>
  <badge-display>
    {{ event }}
  </badge-display>
</template>
