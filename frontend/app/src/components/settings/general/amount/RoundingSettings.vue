<script setup lang="ts">
import type { RoundingMode } from '@/types/settings/frontend-settings';
import { type BigNumber, bigNumberify } from '@rotki/common';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import RoundingSelector from '@/components/settings/general/amount/RoundingSelector.vue';
import { useFrontendSettingsStore } from '@/store/settings/frontend';

const frontendSettingsStore = useFrontendSettingsStore();
const { amountRoundingMode, valueRoundingMode } = storeToRefs(frontendSettingsStore);

const numberExample: BigNumber = bigNumberify(0.0815);

async function setAmountRoundingMode(mode: RoundingMode) {
  await frontendSettingsStore.updateSetting({
    amountRoundingMode: mode,
  });
}

async function setValueRoundingMode(mode: RoundingMode) {
  await frontendSettingsStore.updateSetting({
    valueRoundingMode: mode,
  });
}

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <div class="rounding-settings">
    <div class="flex flex-col space-y-6">
      <RoundingSelector
        :model-value="amountRoundingMode"
        :label="t('rounding_settings.amount_rounding')"
        :hint="t('rounding_settings.amount_rounding_hint')"
        @update:model-value="setAmountRoundingMode($event)"
      >
        <AmountDisplay
          class="ml-2 mt-4"
          :value="numberExample"
        />
      </RoundingSelector>
      <RoundingSelector
        :model-value="valueRoundingMode"
        :label="t('rounding_settings.value_rounding')"
        :hint="t('rounding_settings.value_rounding_hint')"
        @update:model-value="setValueRoundingMode($event)"
      >
        <AmountDisplay
          class="ml-2 mt-4"
          :value="numberExample"
          fiat-currency="USD"
        />
      </RoundingSelector>
    </div>
  </div>
</template>
