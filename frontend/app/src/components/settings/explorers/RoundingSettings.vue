<template>
  <div class="rounding-settings">
    <div class="text-h6 mt-4">
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
          <amount-display class="ms-2" :value="amountExample" />
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
            :value="valueExample"
            fiat-currency="USD"
          />
        </rounding-selector>
      </v-col>
    </v-row>
  </div>
</template>

<script lang="ts">
import { BigNumber } from '@rotki/common';
import { Component, Mixins } from 'vue-property-decorator';
import { mapState } from 'vuex';
import RoundingSelector from '@/components/settings/explorers/RoundingSelector.vue';
import SettingsMixin from '@/mixins/settings-mixin';
import {
  AMOUNT_ROUNDING_MODE,
  RoundingMode,
  VALUE_ROUNDING_MODE
} from '@/types/frontend-settings';
import { bigNumberify } from '@/utils/bignumbers';

@Component({
  components: { RoundingSelector },
  computed: {
    ...mapState('settings', [AMOUNT_ROUNDING_MODE, VALUE_ROUNDING_MODE])
  }
})
export default class RoundingSettings extends Mixins(SettingsMixin) {
  amountRoundingMode!: RoundingMode;
  valueRoundingMode!: RoundingMode;

  readonly amountExample: BigNumber = bigNumberify(0.0815);
  readonly valueExample: BigNumber = bigNumberify(0.0815);

  async setAmountRoundingMode(mode: RoundingMode) {
    await this.updateSetting({
      [AMOUNT_ROUNDING_MODE]: mode
    });
  }

  async setValueRoundingMode(mode: RoundingMode) {
    await this.updateSetting({
      [VALUE_ROUNDING_MODE]: mode
    });
  }
}
</script>
