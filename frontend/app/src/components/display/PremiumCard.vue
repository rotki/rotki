<script setup lang="ts">
import PremiumLock from '@/components/premium/PremiumLock.vue';

defineProps({
  title: {
    required: true,
    type: String
  }
});
</script>

<template>
  <v-card>
    <v-card-title>
      {{ title }}
      <v-spacer />
      <premium-lock />
    </v-card-title>
  </v-card>
</template>
