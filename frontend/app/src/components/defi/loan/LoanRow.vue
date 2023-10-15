<script setup lang="ts">
withDefaults(defineProps<{ title?: string; medium?: boolean }>(), {
  title: '',
  medium: true
});
</script>

<template>
  <div
    class="flex justify-between py-1"
    :class="{
      'font-weight-medium': medium
    }"
  >
    <div>
      {{ title }}
    </div>
    <div>
      <slot />
    </div>
  </div>
</template>
