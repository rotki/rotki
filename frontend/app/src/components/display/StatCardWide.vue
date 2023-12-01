<script setup lang="ts">
withDefaults(
  defineProps<{
    locked?: boolean;
  }>(),
  {
    locked: false
  }
);
</script>

<template>
  <RuiCard no-padding>
    <div
      v-if="!locked"
      class="flex flex-col md:flex-row divide-y md:divide-y-0 md:divide-x"
    >
      <slot />
    </div>
    <div v-else>
      <PremiumLock />
    </div>
  </RuiCard>
</template>
