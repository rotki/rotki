<script setup lang="ts">
import LogLevelSetting from '@/modules/settings/backend/LogLevelSetting.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

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
    <LogLevelSetting />
  </SettingCategory>
</template>
