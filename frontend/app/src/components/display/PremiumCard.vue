<script setup lang="ts">
import PremiumLock from '@/components/premium/PremiumLock.vue';
import CardTitle from '@/components/typography/CardTitle.vue';

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
