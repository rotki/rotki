<script setup lang="ts">
import { msg } from '@/message-key';
import { NoteLocation } from '@/modules/core/common/notes';
import { PremiumStatistics } from '@/modules/premium/premium';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import StatisticPlaceholder from '@/modules/statistics/StatisticPlaceholder.vue';

definePage({
  meta: {
    nav: { labelKey: msg.$t('navigation_menu.statistics_sub.graphs'), icon: 'lu-chart-line', parent: '/statistics/', order: 10, drawer: 'statistics-graph' },
    noteLocation: NoteLocation.STATISTICS,
  },
});

const { allowed } = useFeatureAccess(PremiumFeature.GRAPHS_VIEW);
</script>

<template>
  <div class="container">
    <PremiumStatistics v-if="allowed" />
    <StatisticPlaceholder v-else />
  </div>
</template>
