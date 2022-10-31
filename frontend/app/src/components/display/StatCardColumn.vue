<template>
  <dl>
    <dt
      class="text-h6 font-weight-regular"
      :class="lock ? 'd-flex justify-space-between' : ''"
    >
      <slot name="title" />
    </dt>
    <dd class="primary--text text-h5 font-weight-bold">
      <slot />
    </dd>
  </dl>
</template>

<script setup lang="ts">
defineProps({
  lock: { required: false, type: Boolean, default: false }
});
</script>
