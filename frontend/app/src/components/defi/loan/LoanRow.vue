<script setup lang="ts">
withDefaults(defineProps<{ title?: string; medium?: boolean }>(), {
  medium: true,
  title: '',
});
</script>

<template>
  <div
    class="flex justify-between py-1"
    :class="{
      'font-medium': medium,
    }"
  >
    <div>
      <slot name="title">
        {{ title }}
      </slot>
    </div>
    <div>
      <slot />
    </div>
  </div>
</template>
