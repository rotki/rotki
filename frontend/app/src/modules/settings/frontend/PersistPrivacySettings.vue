<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingSwitch
    setting="persistPrivacySettings"
    class="my-2"
    :label="t('frontend_settings.persist_privacy.label')"
    :hint="t('frontend_settings.persist_privacy.hint')"
    :error-message="t('frontend_settings.persist_privacy.validation.error')"
  />
</template>
