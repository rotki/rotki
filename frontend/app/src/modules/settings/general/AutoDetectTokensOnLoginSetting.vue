<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingSwitch
    setting="autoDetectTokensOnLogin"
    data-cy="auto-detect-tokens-on-login-toggle"
    :label="t('general_settings.auto_detect_tokens_on_login.label')"
    :error-message="t('general_settings.auto_detect_tokens_on_login.validation.error')"
  />
</template>
