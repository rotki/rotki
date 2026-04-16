<script setup lang="ts">
import DatabaseInformation from '@/modules/settings/database/DatabaseInformation.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('database_settings.database_info.title') }}
    </template>
    <template #subtitle>
      {{ t('database_settings.database_info.subtitle') }}
    </template>
    <DatabaseInformation />
  </SettingCategory>
</template>
