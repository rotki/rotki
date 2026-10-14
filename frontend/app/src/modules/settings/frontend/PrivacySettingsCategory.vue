<script setup lang="ts">
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import PersistPrivacySettings from '@/modules/settings/frontend/PersistPrivacySettings.vue';
import ScrambleDataSetting from '@/modules/settings/frontend/ScrambleDataSetting.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('frontend_settings.sections.privacy') }}
    </template>
    <ScrambleDataSetting />
    <SettingsItem setting-key="persistPrivacySettings">
      <PersistPrivacySettings />
    </SettingsItem>
  </SettingCategory>
</template>
