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
    <RuiCardHeader class="p-0 mb-4">
      <template #header>
        {{ t('rounding_settings.title') }}
      </template>
      <template #subheader>
        {{ t('rounding_settings.subtitle') }}
      </template>
    </RuiCardHeader>
    <div class="grid md:grid-cols-2 gap-6 mt-4">
      <RoundingSelector
        :value="amountRoundingMode"
        :label="t('rounding_settings.amount_rounding')"
        :hint="t('rounding_settings.amount_rounding_hint')"
        @change="setAmountRoundingMode($event)"
      >
        <AmountDisplay class="ml-2" :value="numberExample" />
      </RoundingSelector>
      <RoundingSelector
        :value="valueRoundingMode"
        :label="t('rounding_settings.value_rounding')"
        :hint="t('rounding_settings.value_rounding_hint')"
        @change="setValueRoundingMode($event)"
      >
        <AmountDisplay
          class="ml-2"
          :value="numberExample"
          fiat-currency="USD"
        />
      </RoundingSelector>
    </div>
  </div>
</template>
