<script setup lang="ts">
import LogLevelSetting from '@/components/settings/backend/LogLevelSetting.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import { SettingsHighlightIds } from '@/composables/settings/types';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('backend_settings.title') }}
    </template>
    <template #subtitle>
      {{ t('backend_settings.subtitle') }}
    </template>
    <LogLevelSetting :id="SettingsHighlightIds.LOG_LEVEL" />
  </SettingCategory>
</template>
