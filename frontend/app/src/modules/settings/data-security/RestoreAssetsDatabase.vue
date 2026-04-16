<script setup lang="ts">
import RestoreAssetDbButton from '@/modules/assets/admin/RestoreAssetDbButton.vue';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingsItem :id="SettingsHighlightIds.RESTORE_ASSETS_DB">
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
