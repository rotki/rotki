<script setup lang="ts">
const modelValue = defineModel<'prices' | 'caches'>({ required: true });

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <RuiTabs
    v-model="modelValue"
    variant="segmented"
    color="primary"
    data-testid="oracle-tabs"
  >
    <RuiTab value="prices">
      {{ t('oracle_prices.tabs.prices') }}
    </RuiTab>
    <RuiTab value="caches">
      {{ t('oracle_prices.tabs.caches') }}
    </RuiTab>
  </RuiTabs>
</template>
