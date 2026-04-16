<script setup lang="ts">
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
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
    <NewlyDetectedTokensMaxCountSetting :id="SettingsHighlightIds.NEWLY_DETECTED_TOKENS_MAX_COUNT" />
    <NewlyDetectedTokensTtlSetting :id="SettingsHighlightIds.NEWLY_DETECTED_TOKENS_TTL" />
  </SettingCategory>
</template>
