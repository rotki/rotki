<script setup lang="ts">
import type { HTMLAttributes } from 'vue';
import ManageCustomAssets from '@/modules/settings/data-security/ManageCustomAssets.vue';
import RestoreAssetsDatabase from '@/modules/settings/data-security/RestoreAssetsDatabase.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';
import AssetUpdate from '@/modules/shell/app/AssetUpdate.vue';
defineProps<
  /* @vue-ignore */ HTMLAttributes
>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory class="pt-5 border-t border-default">
    <template #title>
      {{ t('database_settings.asset_database.title') }}
    </template>
    <AssetUpdate />
    <ManageCustomAssets />
    <RestoreAssetsDatabase />
  </SettingCategory>
</template>
