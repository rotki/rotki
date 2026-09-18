<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingSwitch
    setting="dockShowSummary"
    :label="t('frontend_settings.dock_show_summary.subtitle')"
    :error-message="t('frontend_settings.dock_show_summary.validation.error')"
  />
</template>
