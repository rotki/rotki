<script setup lang="ts">
import type { RoundingMode } from '@/modules/settings/types/frontend-settings';
import { type BigNumber, bigNumberify } from '@rotki/common';
import { FiatDisplay, ValueDisplay } from '@/modules/assets/amount-display/components';
import RoundingSelector from '@/modules/settings/general/amount/RoundingSelector.vue';
import { useFrontendSettingsStore } from '@/modules/settings/use-frontend-settings-store';
import { useSettingsOperations } from '@/modules/settings/use-settings-operations';

const frontendSettingsStore = useFrontendSettingsStore();
const { amountRoundingMode, valueRoundingMode } = storeToRefs(frontendSettingsStore);
const { updateFrontendSetting } = useSettingsOperations();

const numberExample: BigNumber = bigNumberify(0.0815);

async function setAmountRoundingMode(mode: RoundingMode): Promise<void> {
  await updateFrontendSetting({
    amountRoundingMode: mode,
  });
}

async function setValueRoundingMode(mode: RoundingMode): Promise<void> {
  await updateFrontendSetting({
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
        <ValueDisplay
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
        <FiatDisplay
          class="ml-2 mt-4"
          :value="numberExample"
          from="USD"
        />
      </RoundingSelector>
    </div>
  </div>
</template>
