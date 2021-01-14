<template>
  <v-card>
    <v-card-title>
      {{ $t('account_settings_display.title') }}
    </v-card-title>
    <v-card-subtitle>
      {{ $t('account_settings_display.subtitle') }}
    </v-card-subtitle>
    <v-card-text>
      <v-row class="mt-2" align="center">
        <v-col cols="12" sm="6">
          <span class="text--primary">
            {{ $t('account_settings_display.past_cost_basis') }}
          </span>
          <span class="ms-2">
            <v-icon :class="color(accountingSettings.calculatePastCostBasis)">
              {{ icon(accountingSettings.calculatePastCostBasis) }}
            </v-icon>
          </span>
        </v-col>
        <v-col cols="12" sm="6">
          <span class="text--primary">
            {{ $t('account_settings_display.crypto2crypto') }}
          </span>
          <span class="ms-2">
            <v-icon :class="color(accountingSettings.calculatePastCostBasis)">
              {{ icon(accountingSettings.calculatePastCostBasis) }}
            </v-icon>
          </span>
        </v-col>
        <v-col cols="12" sm="6">
          <span class="text--primary">
            {{ $t('account_settings_display.gas_costs') }}
          </span>
          <span class="ms-2">
            <v-icon :class="color(accountingSettings.includeGasCosts)">
              {{ icon(accountingSettings.includeGasCosts) }}
            </v-icon>
          </span>
        </v-col>
        <v-col cols="12" sm="6">
          <span class="text--primary">
            {{ $t('account_settings_display.tax_free_period') }}
          </span>
          <span class="font-weight-medium ms-2">
            <span
              v-if="accountingSettings.taxFreeAfterPeriod !== 0"
              :class="color(accountingSettings.taxFreeAfterPeriod > 0)"
            >
              {{ taxFreePeriod(accountingSettings.taxFreeAfterPeriod) }}
            </span>
            <v-icon
              v-else
              :class="color(accountingSettings.taxFreeAfterPeriod > 0)"
            >
              mdi-close
            </v-icon>
          </span>
        </v-col>
        <v-col cols="12" sm="6">
          <span class="text--primary">
            {{ $t('account_settings_display.account_asset_movement') }}
          </span>
          <span class="ms-2">
            <v-icon :class="color(accountingSettings.includeGasCosts)">
              {{ icon(accountingSettings.includeGasCosts) }}
            </v-icon>
          </span>
        </v-col>
      </v-row>
    </v-card-text>
  </v-card>
</template>

<script lang="ts">
import { Component, Prop, Vue } from 'vue-property-decorator';
import { AccountingSettings } from '@/typing/types';

@Component({})
export default class AccountingSettingsDisplay extends Vue {
  @Prop({ required: true, type: Object })
  accountingSettings!: AccountingSettings;

  color(enabled: boolean): string {
    return enabled
      ? 'accounting-settings-display--yes'
      : 'accounting-settings-display--no';
  }

  icon(enabled: boolean): string {
    return enabled ? 'mdi-check' : 'mdi-close';
  }

  taxFreePeriod(period: number): string {
    const days = period / 86400;
    return this.$t('account_settings_display.days', { days }).toString();
  }
}
</script>

<style scoped lang="scss">
.accounting-settings-display {
  &--yes {
    color: var(--v-rotki-gain-base);
  }

  &--no {
    color: var(--v-rotki-loss-base);
  }
}
</style>
