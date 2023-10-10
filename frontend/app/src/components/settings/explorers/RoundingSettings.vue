<script setup lang="ts">
import { type BigNumber } from '@rotki/common';
import { type RoundingMode } from '@/types/settings/frontend-settings';

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

<template>
  <div class="rounding-settings mt-8">
    <div class="text-h6">
      {{ t('rounding_settings.title') }}
    </div>
    <div class="text-subtitle-1">
      {{ t('rounding_settings.subtitle') }}
    </div>
    <VRow class="mt-4" align="center">
      <VCol cols="12" md="6">
        <RoundingSelector
          :value="amountRoundingMode"
          :label="t('rounding_settings.amount_rounding')"
          :hint="t('rounding_settings.amount_rounding_hint')"
          @change="setAmountRoundingMode($event)"
        >
          <AmountDisplay class="ms-2" :value="numberExample" />
        </RoundingSelector>
      </VCol>
      <VCol cols="12" md="6">
        <RoundingSelector
          :value="valueRoundingMode"
          :label="t('rounding_settings.value_rounding')"
          :hint="t('rounding_settings.value_rounding_hint')"
          @change="setValueRoundingMode($event)"
        >
          <AmountDisplay
            class="ms-2"
            :value="numberExample"
            fiat-currency="USD"
          />
        </RoundingSelector>
      </VCol>
    </VRow>
  </div>
</template>
