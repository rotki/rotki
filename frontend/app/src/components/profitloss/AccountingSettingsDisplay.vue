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
    <div class="grid md:grid-cols-2 gap-2">
      <div class="flex items-center gap-2">
        <div class="text-body-1">
          {{ t('account_settings_display.past_cost_basis') }}
        </div>
        <SuccessDisplay :success="accountingSettings.calculatePastCostBasis" />
      </div>
      <div class="flex items-center gap-2">
        <div class="text-body-1">
          {{ t('account_settings_display.crypto2crypto') }}
        </div>
        <SuccessDisplay :success="accountingSettings.includeCrypto2crypto" />
      </div>
      <div class="flex items-center gap-2">
        <div class="text-body-1">
          {{ t('account_settings_display.gas_costs') }}
        </div>
        <SuccessDisplay :success="accountingSettings.includeGasCosts" />
      </div>
      <div class="flex items-center gap-2">
        <div class="text-body-1">
          {{ t('account_settings_display.profit_currency') }}
        </div>
        <div>
          {{ accountingSettings.profitCurrency }}
        </div>
      </div>
      <div class="flex items-center gap-2">
        <div class="text-body-1">
          {{ t('account_settings_display.account_asset_movement') }}
        </div>
        <SuccessDisplay
          :success="accountingSettings.accountForAssetsMovements"
        />
      </div>
      <div class="flex items-center gap-2">
        <div class="text-body-1">
          {{ t('account_settings_display.tax_free_period') }}
        </div>
        <div
          v-if="accountingSettings.taxfreeAfterPeriod"
          class="text-body-1 text-rui-text-secondary"
        >
          {{ taxFreePeriod(accountingSettings.taxfreeAfterPeriod) }}
        </div>
        <SuccessDisplay v-else />
      </div>

      <div
        v-if="
          accountingSettings.ethStakingTaxableAfterWithdrawalEnabled !==
          undefined
        "
        class="flex items-center gap-2"
      >
        <div class="text-body-1">
          {{
            t(
              'account_settings_display.eth_staking_taxable_after_withdrawal_enabled'
            )
          }}
        </div>
        <SuccessDisplay
          :success="accountingSettings.ethStakingTaxableAfterWithdrawalEnabled"
        />
      </div>
      <div v-if="costBasisMethodItem" class="flex items-center gap-2">
        <div class="text-body-1">
          {{ t('account_settings_display.cost_basis_method') }}
        </div>
        <div class="text-body-1 text-rui-text-secondary">
          <div class="uppercase">
            {{ costBasisMethodItem.identifier }}
          </div>
          <div>({{ costBasisMethodItem.label }})</div>
        </div>
      </div>
    </div>
  </Card>
</template>
