<script setup lang="ts">
import { NoteLocation } from '@/types/notes';
import { usePremium } from '@/composables/premium';
import NoPremiumPlaceholder from '@/components/premium/NoPremiumPlaceholder.vue';
import WrappedContainer from '@/components/wrapped/WrappedContainer.vue';

definePage({
  meta: {
    noteLocation: NoteLocation.STATISTICS_HISTORY_EVENTS,
  },
  name: 'statistics-history-events',
});

const premium = usePremium();
const { t } = useI18n();
</script>

<template>
  <div class="container">
    <NoPremiumPlaceholder
      v-if="!premium"
      :text="t('statistics.no_premium_label')"
    />
    <div
      v-else
      class="max-w-[800px] mx-auto"
    >
      <WrappedContainer />
    </div>
  </div>
</template>
