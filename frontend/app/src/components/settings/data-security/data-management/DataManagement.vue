<script setup lang="ts">
import PurgeData from '@/components/settings/data-security/data-management/PurgeData.vue';
import PurgeImagesCache from '@/components/settings/data-security/data-management/PurgeImagesCache.vue';
import RefreshCache from '@/components/settings/data-security/data-management/RefreshCache.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';

const { t } = useI18n();
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
