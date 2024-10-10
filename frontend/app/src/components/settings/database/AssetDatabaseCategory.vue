<script setup lang="ts">
const { t } = useI18n();
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('database_settings.asset_database.title') }}
    </template>
    <template #subtitle>
      {{ t('database_settings.asset_database.subtitle') }}
    </template>
    <AssetUpdate />
    <RestoreAssetsDatabase />
  </SettingCategory>
</template>
