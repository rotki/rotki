<script setup lang="ts">
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import SettingCategory from '@/modules/settings/SettingCategory.vue';
import NewlyDetectedTokensMaxCountSetting from './NewlyDetectedTokensMaxCountSetting.vue';
import NewlyDetectedTokensTtlSetting from './NewlyDetectedTokensTtlSetting.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory>
    <template #title>
      {{ t('frontend_settings.newly_detected_tokens.title') }}
    </template>
    <template #subtitle>
      {{ t('frontend_settings.newly_detected_tokens.subtitle') }}
    </template>
    <SettingsItem setting-key="newlyDetectedTokensMaxCount">
      <NewlyDetectedTokensMaxCountSetting />
    </SettingsItem>
    <SettingsItem setting-key="newlyDetectedTokensTtlDays">
      <NewlyDetectedTokensTtlSetting />
    </SettingsItem>
  </SettingCategory>
</template>
