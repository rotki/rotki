<script setup lang="ts">
import SettingNumber from '@/modules/settings/controls/SettingNumber.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingNumber
    setting="oraclePenaltyThresholdCount"
    :label="t('oracle_cache_management.penalty.labels.oracle_penalty_threshold_count')"
    :min="1"
  />
</template>
