<script setup lang="ts">
defineProps({
  title: {
    required: true,
    type: String
  }
});
</script>

<template>
  <VCard>
    <VCardTitle>
      {{ title }}
      <VSpacer />
      <PremiumLock />
    </VCardTitle>
  </VCard>
</template>
