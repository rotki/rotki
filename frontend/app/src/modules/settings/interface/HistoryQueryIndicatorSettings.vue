<script setup lang="ts">
import HistoryQueryIndicatorDismissalThresholdSetting from './HistoryQueryIndicatorDismissalThresholdSetting.vue';
import HistoryQueryIndicatorMinOutOfSyncPeriodSetting from './HistoryQueryIndicatorMinOutOfSyncPeriodSetting.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="font-medium mt-4">
    {{ t('frontend_settings.history_query_indicator.title') }}
  </div>
  <HistoryQueryIndicatorMinOutOfSyncPeriodSetting />
  <HistoryQueryIndicatorDismissalThresholdSetting />
</template>
