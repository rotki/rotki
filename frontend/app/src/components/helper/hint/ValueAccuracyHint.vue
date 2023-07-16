<script setup lang="ts">
import { CURRENCY_USD } from '@/types/currencies';

const { t } = useI18n();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const notUsd = computed(() => get(currencySymbol) !== CURRENCY_USD);
</script>

<template>
  <VTooltip v-if="notUsd" open-delay="400" top>
    <template #activator="{ on, attrs }">
      <VIcon v-bind="attrs" small class="mx-2" v-on="on">
        mdi-information
      </VIcon>
    </template>
    <span>{{ t('price_accuracy_hint.tooltip') }}</span>
  </VTooltip>
</template>
