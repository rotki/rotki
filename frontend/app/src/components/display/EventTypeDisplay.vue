<script setup lang="ts">
const props = defineProps<{ eventType: string }>();
const { eventType } = toRefs(props);

const event = computed<string>(() =>
  get(eventType) === 'comp' ? 'comp claimed' : get(eventType)
);
</script>

<template>
  <BadgeDisplay>
    {{ event }}
  </BadgeDisplay>
</template>
