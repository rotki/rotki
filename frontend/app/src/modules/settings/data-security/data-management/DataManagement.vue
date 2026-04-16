<script setup lang="ts">
import PurgeData from '@/modules/settings/data-security/data-management/PurgeData.vue';
import PurgeImagesCache from '@/modules/settings/data-security/data-management/PurgeImagesCache.vue';
import RefreshCache from '@/modules/settings/data-security/data-management/RefreshCache.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory class="pt-5 border-t border-default">
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
