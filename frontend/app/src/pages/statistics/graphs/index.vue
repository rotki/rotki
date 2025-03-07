<script setup lang="ts">
import StatisticPlaceholder from '@/components/graphs/StatisticPlaceholder.vue';
import { usePremium } from '@/composables/premium';
import { PremiumStatistics } from '@/premium/premium';
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.STATISTICS,
  },
  name: 'statistics-graphs',
});

const premium = usePremium();
</script>

<template>
  <div class="container">
    <PremiumStatistics v-if="premium" />
    <StatisticPlaceholder v-else />
  </div>
</template>
