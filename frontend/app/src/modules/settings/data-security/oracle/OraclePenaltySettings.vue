<script setup lang="ts">
import OraclePenaltyDurationSetting from '@/modules/settings/data-security/oracle/OraclePenaltyDurationSetting.vue';
import OraclePenaltyThresholdCountSetting
  from '@/modules/settings/data-security/oracle/OraclePenaltyThresholdCountSetting.vue';
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

    <OraclePenaltyDurationSetting />
    <OraclePenaltyThresholdCountSetting />
  </SettingCategory>
</template>
