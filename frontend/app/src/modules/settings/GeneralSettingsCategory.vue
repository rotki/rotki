<script setup lang="ts">
import type { HTMLAttributes } from 'vue';
import LogLevelSetting from '@/modules/settings/backend/LogLevelSetting.vue';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import AskUserUponSizeDiscrepancySetting from '@/modules/settings/general/AskUserUponSizeDiscrepancySetting.vue';
import IpfsGatewaySetting from '@/modules/settings/general/IpfsGatewaySetting.vue';
import UsageAnalyticsSetting from '@/modules/settings/general/UsageAnalyticsSetting.vue';
import VersionUpdateFrequencySetting from '@/modules/settings/general/VersionUpdateFrequencySetting.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';
defineProps<
  /* @vue-ignore */ HTMLAttributes
>();

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('general_settings.application.title') }}
    </template>
    <SettingsItem setting-key="submitUsageAnalytics">
      <UsageAnalyticsSetting />
    </SettingsItem>
    <VersionUpdateFrequencySetting />
    <AskUserUponSizeDiscrepancySetting />
    <LogLevelSetting />
    <SettingsItem setting-key="ipfsGateway">
      <template #subtitle>
        {{ t('general_settings.ipfs_gateway.subtitle') }}
      </template>
      <IpfsGatewaySetting />
    </SettingsItem>
  </SettingCategory>
</template>
