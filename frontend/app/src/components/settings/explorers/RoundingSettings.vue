<template>
  <div class="rounding-settings mt-8">
    <div class="text-h6">
      {{ t('rounding_settings.title') }}
    </div>
    <div class="text-subtitle-1">
      {{ t('rounding_settings.subtitle') }}
    </div>
    <v-row class="mt-4" align="center">
      <v-col cols="12" md="6">
        <rounding-selector
          :value="amountRoundingMode"
          :label="t('rounding_settings.amount_rounding')"
          :hint="t('rounding_settings.amount_rounding_hint')"
          @change="setAmountRoundingMode($event)"
        >
          <amount-display class="ms-2" :value="numberExample" />
        </rounding-selector>
      </v-col>
      <v-col cols="12" md="6">
        <rounding-selector
          :value="valueRoundingMode"
          :label="t('rounding_settings.value_rounding')"
          :hint="t('rounding_settings.value_rounding_hint')"
          @change="setValueRoundingMode($event)"
        >
          <amount-display
            class="ms-2"
            :value="numberExample"
            fiat-currency="USD"
          />
        </rounding-selector>
      </v-col>
    </v-row>
  </div>
</template>

<script setup lang="ts">
import { BigNumber } from '@rotki/common';
import RoundingSelector from '@/components/settings/explorers/RoundingSelector.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';
import { RoundingMode } from '@/types/frontend-settings';
import { bigNumberify } from '@/utils/bignumbers';

const frontendSettingsStore = useFrontendSettingsStore();
const { amountRoundingMode, valueRoundingMode } = storeToRefs(
  frontendSettingsStore
);

const numberExample: BigNumber = bigNumberify(0.0815);

const setAmountRoundingMode = async (mode: RoundingMode) => {
  await frontendSettingsStore.updateSetting({
    amountRoundingMode: mode
  });
};

const setValueRoundingMode = async (mode: RoundingMode) => {
  await frontendSettingsStore.updateSetting({
    valueRoundingMode: mode
  });
};

const { t } = useI18n();
</script>
