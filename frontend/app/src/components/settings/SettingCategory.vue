<script setup lang="ts">
const slots = useSlots();
</script>

<template>
  <RuiCard>
    <template #header>
      <slot name="title" />
    </template>
    <template
      v-if="slots.subtitle"
      #subheader
    >
      <slot name="subtitle" />
    </template>
    <slot />
  </RuiCard>
</template>
