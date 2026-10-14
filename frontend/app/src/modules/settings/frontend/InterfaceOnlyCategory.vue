<script setup lang="ts">
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import AnimationsEnabledSetting from '@/modules/settings/frontend/AnimationsEnabledSetting.vue';
import DockShowSummarySetting from '@/modules/settings/frontend/DockShowSummarySetting.vue';
import PersistTableSortingSetting from '@/modules/settings/frontend/PersistTableSortingSetting.vue';
import LanguageSetting from '@/modules/settings/general/language/LanguageSetting.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('frontend_settings.sections.display') }}
    </template>
    <LanguageSetting />
    <SettingsItem setting-key="animationsEnabled">
      <AnimationsEnabledSetting />
    </SettingsItem>
    <SettingsItem setting-key="persistTableSorting">
      <PersistTableSortingSetting />
    </SettingsItem>
    <SettingsItem setting-key="dockShowSummary">
      <DockShowSummarySetting />
    </SettingsItem>
  </SettingCategory>
</template>
