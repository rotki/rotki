<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingSwitch
    setting="autoCreateProfitEvents"
    :label="t('general_settings.history_event.auto_create_profit_events.label')"
    :error-message="t('general_settings.history_event.auto_create_profit_events.validation.error')"
  />
</template>
