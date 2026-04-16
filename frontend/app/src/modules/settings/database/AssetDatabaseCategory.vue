<script setup lang="ts">
import RestoreAssetsDatabase from '@/modules/settings/data-security/RestoreAssetsDatabase.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';
import AssetUpdate from '@/modules/shell/app/AssetUpdate.vue';

const { t } = useI18n({ useScope: 'global' });
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
