<script setup lang="ts">
import RestoreAssetDbButton from '@/modules/assets/admin/RestoreAssetDbButton.vue';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsItem action-key="restoreAssetsDb">
    <template #title>
      {{ t('asset_update.restore.title') }}
    </template>
    <template #subtitle>
      {{ t('asset_update.restore.subtitle') }}
    </template>
    <RestoreAssetDbButton />
  </SettingsItem>
</template>
