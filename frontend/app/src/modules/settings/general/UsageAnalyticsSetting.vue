<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingSwitch
    setting="submitUsageAnalytics"
    data-testid="anonymous-usage-statistics-input"
    :label="t('general_settings.usage_analytics.label')"
    :error-message="t('general_settings.usage_analytics.validation.error')"
  />
</template>
