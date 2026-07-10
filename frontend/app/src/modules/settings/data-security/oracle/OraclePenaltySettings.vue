<script setup lang="ts">
import SettingsItem from '@/modules/settings/controls/SettingsItem.vue';
import OraclePenaltyDurationSetting from '@/modules/settings/data-security/oracle/OraclePenaltyDurationSetting.vue';
import OraclePenaltyThresholdCountSetting
  from '@/modules/settings/data-security/oracle/OraclePenaltyThresholdCountSetting.vue';
import { SettingsHighlightIds } from '@/modules/settings/setting-highlight-ids';
import SettingCategory from '@/modules/settings/SettingCategory.vue';

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <SettingCategory class="pt-5 border-t border-default">
    <template #title>
      {{ t('oracle_cache_management.penalty.title') }}
    </template>
    <template #subtitle>
      {{ t('oracle_cache_management.penalty.subtitle') }}
    </template>

    <SettingsItem :id="SettingsHighlightIds.ORACLE_PENALTY_DURATION">
      <template #title>
        {{ t('oracle_cache_management.penalty.labels.oracle_penalty_duration') }}
      </template>
      <template #subtitle>
        {{ t('oracle_cache_management.penalty.hints.oracle_penalty_duration') }}
      </template>
      <OraclePenaltyDurationSetting />
    </SettingsItem>
    <SettingsItem :id="SettingsHighlightIds.ORACLE_PENALTY_THRESHOLD">
      <template #title>
        {{ t('oracle_cache_management.penalty.labels.oracle_penalty_threshold_count') }}
      </template>
      <template #subtitle>
        {{ t('oracle_cache_management.penalty.hints.oracle_penalty_threshold_count') }}
      </template>
      <OraclePenaltyThresholdCountSetting />
    </SettingsItem>
  </SettingCategory>
</template>
