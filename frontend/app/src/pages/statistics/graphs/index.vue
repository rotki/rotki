<script setup lang="ts">
import { NoteLocation } from '@/modules/core/common/notes';
import { PremiumStatistics } from '@/modules/premium/premium';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import StatisticPlaceholder from '@/modules/statistics/StatisticPlaceholder.vue';

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
