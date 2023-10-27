<script setup lang="ts">
defineProps<{ title: string }>();
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
