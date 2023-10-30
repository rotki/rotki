<script setup lang="ts">
withDefaults(defineProps<{ lock?: boolean }>(), { lock: false });
</script>

<template>
  <dl>
    <dt
      class="text-h6 font-regular"
      :class="lock ? 'flex justify-space-between' : ''"
    >
      <slot name="title" />
    </dt>
    <dd class="text-rui-text text-h5 font-bold">
      <slot />
    </dd>
  </dl>
</template>
