<script setup lang="ts">
defineProps<{
  finished: boolean;
}>();
</script>

<template>
  <div>
    <div v-if="finished">
      <slot name="finished" />
    </div>
    <div v-else>
      <slot name="running" />
    </div>
  </div>
</template>
