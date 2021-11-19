<template>
  <setting-category>
    <template #title>
      {{ $t('price_oracle_settings.title') }}
    </template>
    <template #subtitle>
      {{ $t('price_oracle_settings.subtitle') }}
    </template>

    <v-row>
      <v-col cols="12" md="6">
        <price-oracle-selection
          :value="currentOracles"
          :all-items="availableOracles"
          :status="currentError"
          @input="onCurrentChange($event)"
        >
          <template #title>
            {{ $t('price_oracle_settings.current_prices') }}
          </template>
        </price-oracle-selection>
      </v-col>

      <v-col cols="12" md="6">
        <price-oracle-selection
          :value="historicOracles"
          :all-items="availableOracles"
          :status="historicError"
          @input="onHistoricChange($event)"
        >
          <template #title>
            {{ $t('price_oracle_settings.historic_prices') }}
          </template>
        </price-oracle-selection>
      </v-col>
    </v-row>
    <v-row>
      <v-col class="text-caption">
        {{ $t('price_oracle_selection.hint') }}
      </v-col>
    </v-row>
  </setting-category>
</template>

<script lang="ts">
import { Component, Mixins } from 'vue-property-decorator';
import PriceOracleSelection from '@/components/settings/PriceOracleSelection.vue';
import SettingCategory from '@/components/settings/SettingCategory.vue';
import SettingsMixin from '@/mixins/settings-mixin';
import { ActionStatus } from '@/store/types';
import { PriceOracle } from '@/types/user';

@Component({
  components: { PriceOracleSelection, SettingCategory }
})
export default class PriceOracleSettings extends Mixins(SettingsMixin) {
  readonly availableOracles: string[] = ['cryptocompare', 'coingecko'];

  currentOracles: string[] = [];
  historicOracles: string[] = [];

  currentError: ActionStatus | null = null;
  historicError: ActionStatus | null = null;

  mounted() {
    this.currentOracles = this.generalSettings.currentPriceOracles;
    this.historicOracles = this.generalSettings.historicalPriceOracles;
  }

  async onCurrentChange(oracles: PriceOracle[]) {
    this.currentError = null;
    const previous = [...this.currentOracles];
    this.currentOracles = oracles;
    const status = await this.settingsUpdate({
      currentPriceOracles: oracles
    });
    if (!status.success) {
      this.currentError = status;
      this.currentOracles = previous;
    }
  }

  async onHistoricChange(oracles: PriceOracle[]) {
    this.historicError = null;
    const previous = [...this.historicOracles];
    this.historicOracles = oracles;
    const status = await this.settingsUpdate({
      historicalPriceOracles: oracles
    });
    if (!status.success) {
      this.historicError = status;
      this.historicOracles = previous;
    }
  }
}
</script>
