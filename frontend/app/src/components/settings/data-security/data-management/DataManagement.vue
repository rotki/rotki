<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('data_management.title') }}
    </template>
    <template #subtitle>
      {{ t('database_settings.manage_data.subtitle') }}
    </template>
    <PurgeData />
    <PurgeImagesCache />
    <RefreshCache />
  </SettingCategory>
</template>
