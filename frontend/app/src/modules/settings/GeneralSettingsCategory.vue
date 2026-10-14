<script setup lang="ts">
import LogLevelSetting from '@/modules/settings/backend/LogLevelSetting.vue';
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import AskUserUponSizeDiscrepancySetting from '@/modules/settings/general/AskUserUponSizeDiscrepancySetting.vue';
import UsageAnalyticsSetting from '@/modules/settings/general/UsageAnalyticsSetting.vue';
import VersionUpdateFrequencySetting from '@/modules/settings/general/VersionUpdateFrequencySetting.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

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
  </SettingCategory>
</template>
