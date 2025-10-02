<script setup lang="ts">
import StatisticPlaceholder from '@/components/graphs/StatisticPlaceholder.vue';
import { usePremiumHelper } from '@/composables/premium';
import { PremiumStatistics } from '@/premium/premium';
import { NoteLocation } from '@/types/notes';

definePage({
  meta: {
    noteLocation: NoteLocation.STATISTICS,
  },
  name: 'statistics-graphs',
});

const { isFeatureAllowed } = usePremiumHelper();

const allowed = isFeatureAllowed('graphsView');
</script>

<template>
  <div class="container">
    <PremiumStatistics v-if="allowed" />
    <StatisticPlaceholder v-else />
  </div>
</template>
