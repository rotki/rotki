<script setup lang="ts">
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import Explorers from '@/modules/settings/explorers/Explorers.vue';
import AnimationsEnabledSetting from '@/modules/settings/frontend/AnimationsEnabledSetting.vue';
import PersistPrivacySettings from '@/modules/settings/frontend/PersistPrivacySettings.vue';
import PersistTableSortingSetting from '@/modules/settings/frontend/PersistTableSortingSetting.vue';
import ScrambleDataSetting from '@/modules/settings/frontend/ScrambleDataSetting.vue';
import LanguageSetting from '@/modules/settings/general/language/LanguageSetting.vue';
import QueryPeriodSetting from '@/modules/settings/general/QueryPeriodSetting.vue';
import RefreshSetting from '@/modules/settings/general/RefreshSetting.vue';
import HistoryQueryIndicatorSettings from '@/modules/settings/interface/HistoryQueryIndicatorSettings.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('frontend_settings.title') }}
    </template>
    <LanguageSetting />
    <SettingsItem setting-key="animationsEnabled">
      <AnimationsEnabledSetting />
    </SettingsItem>
    <SettingsItem setting-key="persistTableSorting">
      <PersistTableSortingSetting />
    </SettingsItem>
    <ScrambleDataSetting />
    <SettingsItem setting-key="persistPrivacySettings">
      <PersistPrivacySettings />
    </SettingsItem>
    <RefreshSetting />
    <SettingsItem setting-key="queryPeriod">
      <QueryPeriodSetting />
    </SettingsItem>
    <Explorers />
    <HistoryQueryIndicatorSettings />
  </SettingCategory>
</template>
