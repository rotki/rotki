<script setup lang="ts">
import {
  type BaseAccountingSettings,
  type CostBasisMethod
} from '@/types/user';
import { type ActionDataEntry } from '@/types/action';

const props = defineProps<{ accountingSettings: BaseAccountingSettings }>();

const { accountingSettings } = toRefs(props);
const { t } = useI18n();
const { costBasisMethodData } = useCostBasisMethod();
const color = (enabled: boolean | null) =>
  enabled
    ? 'accounting-settings-display--yes'
    : 'accounting-settings-display--no';

const icon = (enabled: boolean | null) => (enabled ? 'mdi-check' : 'mdi-close');

const taxFreePeriod = (period: number) => {
  const days = period / 86400;
  return t('account_settings_display.days', { days });
};

const costBasisMethodItem = computed<ActionDataEntry<CostBasisMethod> | null>(
  () => {
    const method = get(accountingSettings).costBasisMethod;
    if (!method) {
      return null;
    }
    return (
      get(costBasisMethodData).find(item => item.identifier === method) || null
    );
  }
);
</script>

<template>
  <Card>
    <template #title>{{ t('account_settings_display.title') }}</template>
    <template #subtitle>
      {{ t('account_settings_display.subtitle') }}
    </template>
    <VRow class="mt-2">
      <VCol cols="12" sm="6">
        <span class="text--primary">
          {{ t('account_settings_display.past_cost_basis') }}
        </span>
        <span class="ms-2">
          <VIcon :class="color(accountingSettings.calculatePastCostBasis)">
            {{ icon(accountingSettings.calculatePastCostBasis) }}
          </VIcon>
        </span>
      </VCol>
      <VCol cols="12" sm="6">
        <span class="text--primary">
          {{ t('account_settings_display.crypto2crypto') }}
        </span>
        <span class="ms-2">
          <VIcon :class="color(accountingSettings.includeCrypto2crypto)">
            {{ icon(accountingSettings.includeCrypto2crypto) }}
          </VIcon>
        </span>
      </VCol>
      <VCol cols="12" sm="6">
        <span class="text--primary">
          {{ t('account_settings_display.gas_costs') }}
        </span>
        <span class="ms-2">
          <VIcon :class="color(accountingSettings.includeGasCosts)">
            {{ icon(accountingSettings.includeGasCosts) }}
          </VIcon>
        </span>
      </VCol>
      <VCol cols="12" sm="6">
        <span class="text--primary">
          {{ t('account_settings_display.profit_currency') }}
        </span>
        <span class="ms-2">
          {{ accountingSettings.profitCurrency }}
        </span>
      </VCol>
      <VCol cols="12" sm="6">
        <span class="text--primary">
          {{ t('account_settings_display.account_asset_movement') }}
        </span>
        <span class="ms-2">
          <VIcon :class="color(accountingSettings.accountForAssetsMovements)">
            {{ icon(accountingSettings.accountForAssetsMovements) }}
          </VIcon>
        </span>
      </VCol>
      <VCol cols="12" sm="6">
        <span class="text--primary">
          {{ t('account_settings_display.tax_free_period') }}
        </span>
        <span class="font-medium ms-2">
          <span
            v-if="accountingSettings.taxfreeAfterPeriod"
            :class="color(accountingSettings.taxfreeAfterPeriod > 0)"
          >
            {{ taxFreePeriod(accountingSettings.taxfreeAfterPeriod) }}
          </span>
          <VIcon v-else :class="color(false)"> mdi-close </VIcon>
        </span>
      </VCol>

      <VCol
        v-if="
          accountingSettings.ethStakingTaxableAfterWithdrawalEnabled !==
          undefined
        "
        cols="12"
        sm="6"
      >
        <span class="text--primary">
          {{
            t(
              'account_settings_display.eth_staking_taxable_after_withdrawal_enabled'
            )
          }}
        </span>
        <span class="ms-2">
          <VIcon
            :class="
              color(accountingSettings.ethStakingTaxableAfterWithdrawalEnabled)
            "
          >
            {{
              icon(accountingSettings.ethStakingTaxableAfterWithdrawalEnabled)
            }}
          </VIcon>
        </span>
      </VCol>
      <VCol v-if="costBasisMethodItem" cols="12" sm="6">
        <span class="text--primary">
          {{ t('account_settings_display.cost_basis_method') }}
        </span>
        <span class="ms-2">
          <span class="accounting-settings-display--uppercase">
            {{ costBasisMethodItem.identifier }}
          </span>
          <span>({{ costBasisMethodItem.label }})</span>
        </span>
      </VCol>
    </VRow>
  </Card>
</template>

<style scoped lang="scss">
.accounting-settings-display {
  &--yes {
    color: var(--v-rotki-success-base);
  }

  &--no {
    color: var(--v-rotki-error-base);
  }

  &--uppercase {
    text-transform: uppercase;
  }
}
</style>
