<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingSwitch
    setting="displayDateInLocaltime"
    :label="t('general_settings.display_date_in_localtime.label')"
    :error-message="t('general_settings.display_date_in_localtime.validation.error')"
  />
</template>
