<script setup lang="ts">
const { t } = useI18n();
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
