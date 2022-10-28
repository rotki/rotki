<template>
  <v-tooltip v-if="notUsd" open-delay="400" top>
    <template #activator="{ on, attrs }">
      <v-icon v-bind="attrs" small class="mx-2" v-on="on">
        mdi-information
      </v-icon>
    </template>
    <span>{{ t('price_accuracy_hint.tooltip') }}</span>
  </v-tooltip>
</template>

<script setup lang="ts">
import { useGeneralSettingsStore } from '@/store/settings/general';
import { CURRENCY_USD } from '@/types/currencies';

const { t } = useI18n();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const notUsd = computed(() => {
  return get(currencySymbol) !== CURRENCY_USD;
});
</script>
