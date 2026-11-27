<script setup lang="ts">
import { RuiSwitch } from '@rotki/ui-library';
import { useLocalStorage } from '@vueuse/core';
import { useI18n } from 'vue-i18n';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import { AUTO_APPLY_ASSET_UPDATES_KEY } from '@/modules/shell/app/asset-update-keys';

const { t } = useI18n({ useScope: 'global' });

/** Read by the login flow before any profile is open, which is why it lives on this device. */
const autoApply = useLocalStorage<boolean>(AUTO_APPLY_ASSET_UPDATES_KEY, false);
</script>

<template>
  <SettingsItem action-key="assetAutoUpdate">
    <template #title>
      {{ t('asset_update.auto.title') }}
    </template>
    <template #subtitle>
      {{ t('asset_update.auto.subtitle') }}
    </template>
    <RuiSwitch
      v-model="autoApply"
      color="primary"
      :label="t('asset_update.auto.label')"
      details="hidden"
      data-testid="asset-auto-update-toggle"
    />
  </SettingsItem>
</template>
