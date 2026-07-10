<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingSwitch
    setting="autoDetectTokens"
    :label="t('general_settings.auto_detect_tokens.label')"
    :error-message="t('general_settings.auto_detect_tokens.validation.error')"
  />
</template>
