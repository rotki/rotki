<script setup lang="ts">
defineProps<{ title: string }>();
</script>

<template>
  <RuiCard no-padding>
    <CardTitle class="p-4">
      {{ title }}
      <div class="grow" />
      <PremiumLock />
    </CardTitle>
  </RuiCard>
</template>
