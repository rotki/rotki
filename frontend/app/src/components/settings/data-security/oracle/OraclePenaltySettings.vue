<script setup lang="ts">
import OraclePenaltyDurationSetting from '@/components/settings/data-security/oracle/OraclePenaltyDurationSetting.vue';

const { t } = useI18n();
</script>

<template>
  <div class="pt-6 pb-4 flex flex-col gap-4">
    <RuiCardHeader class="px-0">
      <template #header>
        {{ t('oracle_cache_management.penalty.title') }}
      </template>
      <template #subheader>
        {{ t('oracle_cache_management.penalty.subtitle') }}
      </template>
    </RuiCardHeader>
    <OraclePenaltyDurationSetting />
    <OraclePenaltyThresholdCountSetting />
  </div>
</template>
