<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingSwitch
    setting="enableAliasNames"
    class="mt-4"
    :debounce="1500"
    :label="t('frontend_settings.alias_names.label')"
    :error-message="t('frontend_settings.alias_names.validation.error')"
  />
</template>
