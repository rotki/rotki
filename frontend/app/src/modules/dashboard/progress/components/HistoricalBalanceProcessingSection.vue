<script setup lang="ts">
import type { HistoricalBalanceProcessingData } from '@/modules/messaging/types/status-types';

defineProps<{
  progress: HistoricalBalanceProcessingData;
  percentage: number;
}>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiProgress
    circular
    :value="percentage"
    size="30"
    show-label
    thickness="2"
    color="primary"
  />

  <div class="inline gap-2">
    {{ t('historical_balances.processing_progress', { processed: progress.processed, total: progress.total }) }}
  </div>
</template>
