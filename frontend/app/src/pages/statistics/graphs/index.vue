<script setup lang="ts">
import StatisticPlaceholder from '@/components/graphs/StatisticPlaceholder.vue';
import { NoteLocation } from '@/modules/common/notes';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import { PremiumStatistics } from '@/premium/premium';

definePage({
  meta: {
    noteLocation: NoteLocation.STATISTICS,
  },
  name: 'statistics-graphs',
});

const { allowed } = useFeatureAccess(PremiumFeature.GRAPHS_VIEW);
</script>

<template>
  <div class="container">
    <PremiumStatistics v-if="allowed" />
    <StatisticPlaceholder v-else />
  </div>
</template>
