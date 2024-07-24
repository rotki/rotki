<script setup lang="ts">
import { PremiumStatistics } from '@/premium/premium';
import { NoteLocation } from '@/types/notes';

definePage({
  name: 'statistics',
  meta: {
    noteLocation: NoteLocation.STATISTICS,
  },
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
    <PremiumStatistics v-else />
  </div>
</template>
