<template>
  <div class="rounding-settings mt-8">
    <div class="text-h6">
      {{ $t('rounding_settings.title') }}
    </div>
    <div class="text-subtitle-1">
      {{ $t('rounding_settings.subtitle') }}
    </div>
    <v-row class="mt-4" align="center">
      <v-col cols="12" md="6">
        <rounding-selector
          :value="amountRoundingMode"
          :label="$t('rounding_settings.amount_rounding')"
          :hint="$t('rounding_settings.amount_rounding_hint')"
          @change="setAmountRoundingMode($event)"
        >
          <amount-display class="ms-2" :value="numberExample" />
        </rounding-selector>
      </v-col>
      <v-col cols="12" md="6">
        <rounding-selector
          :value="valueRoundingMode"
          :label="$t('rounding_settings.value_rounding')"
          :hint="$t('rounding_settings.value_rounding_hint')"
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

<script lang="ts">
import { BigNumber } from '@rotki/common';
import { defineComponent } from '@vue/composition-api';
import RoundingSelector from '@/components/settings/explorers/RoundingSelector.vue';
import { setupSettings } from '@/composables/settings';
import {
  AMOUNT_ROUNDING_MODE,
  RoundingMode,
  VALUE_ROUNDING_MODE
} from '@/types/frontend-settings';
import { bigNumberify } from '@/utils/bignumbers';

export default defineComponent({
  name: 'RoundingSettings',
  components: { RoundingSelector },
  setup() {
    const { amountRoundingMode, valueRoundingMode, updateSetting } =
      setupSettings();

    const numberExample: BigNumber = bigNumberify(0.0815);

    const setAmountRoundingMode = async (mode: RoundingMode) => {
      await updateSetting({
        [AMOUNT_ROUNDING_MODE]: mode
      });
    };

    const setValueRoundingMode = async (mode: RoundingMode) => {
      await updateSetting({
        [VALUE_ROUNDING_MODE]: mode
      });
    };

    return {
      amountRoundingMode,
      valueRoundingMode,
      numberExample,
      setAmountRoundingMode,
      setValueRoundingMode
    };
  }
});
</script>
