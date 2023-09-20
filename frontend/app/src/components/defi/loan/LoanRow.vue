<script setup lang="ts">
defineProps({
  title: { required: false, type: String, default: '' },
  medium: { required: false, type: Boolean, default: true }
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
