<script setup lang="ts">
import WrappedContainerPlaceholder from '@/components/wrapped/WrappedContainerPlaceholder.vue';
import { usePremiumHelper } from '@/composables/premium';
import WrappedContainer from '@/modules/statistics/wrapped/components/WrappedContainer.vue';
import { NoteLocation } from '@/types/notes';
import { PremiumFeature } from '@/types/session';

definePage({
  meta: {
    noteLocation: NoteLocation.STATISTICS_HISTORY_EVENTS,
  },
  name: 'statistics-history-events',
});

const { isFeatureAllowed } = usePremiumHelper();

const allowed = isFeatureAllowed(PremiumFeature.EVENT_ANALYSIS_VIEW);
</script>

<template>
  <div class="container">
    <RuiCard class="max-w-[920px] mx-auto">
      <WrappedContainer v-if="allowed" />
      <WrappedContainerPlaceholder v-else />
    </RuiCard>
  </div>
</template>
