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
    <SettingsItem>
      <template #title>
        {{ t('data_management.purge_data.title') }}
      </template>
      <template #subtitle>
        {{ t('data_management.purge_data.subtitle') }}
      </template>
      <PurgeData />
    </SettingsItem>
    <SettingsItem>
      <template #title>
        {{ t('data_management.purge_images_cache.title') }}
      </template>
      <template #subtitle>
        {{ t('data_management.purge_images_cache.subtitle') }}
      </template>
      <PurgeImagesCache />
    </SettingsItem>
    <SettingsItem>
      <template #title>
        {{ t('data_management.refresh_cache.title') }}
      </template>
      <template #subtitle>
        {{ t('data_management.refresh_cache.subtitle') }}
      </template>
      <RefreshCache />
    </SettingsItem>
  </SettingCategory>
</template>
