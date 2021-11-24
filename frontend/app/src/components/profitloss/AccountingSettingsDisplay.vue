<template>
  <card>
    <template #title>{{ $t('account_settings_display.title') }}</template>
    <template #subtitle>
      {{ $t('account_settings_display.subtitle') }}
    </template>
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
          <v-icon :class="color(accountingSettings.includeCrypto2crypto)">
            {{ icon(accountingSettings.includeCrypto2crypto) }}
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
            v-if="accountingSettings.taxfreeAfterPeriod !== 0"
            :class="color(accountingSettings.taxfreeAfterPeriod > 0)"
          >
            {{ taxFreePeriod(accountingSettings.taxfreeAfterPeriod) }}
          </span>
          <v-icon
            v-else
            :class="color(accountingSettings.taxfreeAfterPeriod > 0)"
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
          <v-icon :class="color(accountingSettings.accountForAssetsMovements)">
            {{ icon(accountingSettings.accountForAssetsMovements) }}
          </v-icon>
        </span>
      </v-col>
    </v-row>
  </card>
</template>

<script lang="ts">
import { defineComponent, PropType } from '@vue/composition-api';
import i18n from '@/i18n';
import { AccountingSettings } from '@/types/user';

const AccountingSettingsDisplay = defineComponent({
  name: 'AccountingSettingsDisplay',
  props: {
    accountingSettings: {
      required: true,
      type: Object as PropType<AccountingSettings>
    }
  },
  setup() {
    const color = (enabled: boolean) => {
      return enabled
        ? 'accounting-settings-display--yes'
        : 'accounting-settings-display--no';
    };

    const icon = (enabled: boolean) => {
      return enabled ? 'mdi-check' : 'mdi-close';
    };

    const taxFreePeriod = (period: number) => {
      const days = period / 86400;
      return i18n.t('account_settings_display.days', { days }).toString();
    };

    return {
      color,
      icon,
      taxFreePeriod
    };
  }
});

export default AccountingSettingsDisplay;
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
