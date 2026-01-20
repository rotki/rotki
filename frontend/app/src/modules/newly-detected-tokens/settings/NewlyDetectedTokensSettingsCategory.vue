<script setup lang="ts">
import SettingCategory from '@/components/settings/SettingCategory.vue';
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
    <NewlyDetectedTokensMaxCountSetting />
    <NewlyDetectedTokensTtlSetting />
  </SettingCategory>
</template>
