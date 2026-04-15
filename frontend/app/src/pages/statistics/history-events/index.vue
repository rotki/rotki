<script setup lang="ts">
import WrappedContainerPlaceholder from '@/components/wrapped/WrappedContainerPlaceholder.vue';
import { NoteLocation } from '@/modules/common/notes';
import { PremiumFeature, useFeatureAccess } from '@/modules/premium/use-feature-access';
import WrappedContainer from '@/modules/statistics/wrapped/components/WrappedContainer.vue';

definePage({
  meta: {
    noteLocation: NoteLocation.STATISTICS_HISTORY_EVENTS,
  },
  name: 'statistics-history-events',
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
