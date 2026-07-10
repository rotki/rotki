<script setup lang="ts">
import { NoteLocation } from '@/modules/core/common/notes';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import WrappedContainer from '@/modules/statistics/wrapped/components/WrappedContainer.vue';
import WrappedContainerPlaceholder from '@/modules/statistics/WrappedContainerPlaceholder.vue';

definePage({
  meta: {
    nav: { labelKey: 'navigation_menu.statistics_sub.history_events', icon: 'lu-chart-bar', parent: '/statistics/', order: 20, drawer: 'statistics-history-events' },
    noteLocation: NoteLocation.STATISTICS_HISTORY_EVENTS,
  },
});

const { allowed } = useFeatureAccess(PremiumFeature.EVENT_ANALYSIS_VIEW);
</script>

<template>
  <div class="container">
    <RuiCard class="max-w-[920px] mx-auto">
      <WrappedContainer v-if="allowed" />
      <WrappedContainerPlaceholder v-else />
    </RuiCard>
  </div>
</template>
