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
    <SettingsItem>
      <template #title>
        {{ t('asset_update.success.title') }}
      </template>
      <template #subtitle>
        {{ t('asset_update.manual.subtitle') }}
      </template>
      <AssetUpdate />
    </SettingsItem>
    <SettingsItem>
      <template #title>
        {{ t('asset_update.restore.title') }}
      </template>
      <template #subtitle>
        {{ t('asset_update.restore.subtitle') }}
        {{ t('asset_update.restore.warning') }}
      </template>
      <RestoreAssetsDatabase />
    </SettingsItem>
  </SettingCategory>
</template>
