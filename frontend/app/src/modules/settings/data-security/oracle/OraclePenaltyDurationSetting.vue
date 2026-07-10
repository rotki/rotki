<script setup lang="ts">
import SettingNumber from '@/modules/settings/controls/SettingNumber.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingNumber
    setting="oraclePenaltyDuration"
    data-testid="oracle-penalty-duration"
    :label="t('oracle_cache_management.penalty.labels.oracle_penalty_duration')"
    :min="1"
  />
</template>
