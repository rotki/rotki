<script setup lang="ts">
import RestoreAssetDbButton from '@/components/asset-manager/RestoreAssetDbButton.vue';
import SettingsItem from '@/components/settings/controls/SettingsItem.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsItem>
    <template #title>
      {{ t('asset_update.restore.title') }}
    </template>
    <template #subtitle>
      {{ t('asset_update.restore.subtitle') }}
    </template>
    <div class="flex flex-col gap-4">
      <RuiAlert type="warning">
        {{ t('asset_update.restore.warning') }}
      </RuiAlert>
      <RestoreAssetDbButton />
    </div>
  </SettingsItem>
</template>
