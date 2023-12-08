<script setup lang="ts">
defineProps<{ title: string }>();
</script>

<template>
  <VCard>
    <VCardTitle>
      {{ title }}
      <div class="grow" />
      <PremiumLock />
    </VCardTitle>
  </VCard>
</template>
