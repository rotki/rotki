<script setup lang="ts">
import SettingSwitch from '@/modules/settings/controls/SettingSwitch.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingSwitch
    setting="persistTableSorting"
    :label="t('frontend_settings.persist_table_sorting.subtitle')"
    :error-message="t('frontend_settings.persist_table_sorting.validation.error')"
  />
</template>
