<script setup lang="ts">
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
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
    <SettingsItem :id="SettingsHighlightIds.NEWLY_DETECTED_TOKENS_MAX_COUNT">
      <template #title>
        {{ t('frontend_settings.newly_detected_tokens.max_count.title') }}
      </template>
      <NewlyDetectedTokensMaxCountSetting />
    </SettingsItem>
    <SettingsItem :id="SettingsHighlightIds.NEWLY_DETECTED_TOKENS_TTL">
      <template #title>
        {{ t('frontend_settings.newly_detected_tokens.ttl_days.title') }}
      </template>
      <NewlyDetectedTokensTtlSetting />
    </SettingsItem>
  </SettingCategory>
</template>
