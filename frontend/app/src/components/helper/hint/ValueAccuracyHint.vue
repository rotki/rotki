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
import { get } from '@vueuse/core';
import { storeToRefs } from 'pinia';
import { computed } from 'vue';
import { useI18n } from 'vue-i18n-composable';
import { CURRENCY_USD } from '@/data/currencies';
import { useGeneralSettingsStore } from '@/store/settings/general';

const { t } = useI18n();
const { currencySymbol } = storeToRefs(useGeneralSettingsStore());

const notUsd = computed(() => {
  return get(currencySymbol) !== CURRENCY_USD;
});
</script>
