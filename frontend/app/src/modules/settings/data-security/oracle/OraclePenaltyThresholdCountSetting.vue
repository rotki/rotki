<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import SettingNumber from '@/modules/settings/controls/SettingNumber.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingNumber
    setting="oraclePenaltyThresholdCount"
    :label="t('oracle_cache_management.penalty.units.failures')"
    :min="1"
  />
</template>
