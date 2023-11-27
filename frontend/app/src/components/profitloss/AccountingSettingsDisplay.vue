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

type Item = {
  label: string;
  data: boolean | string;
};

const items: ComputedRef<Item[]> = computed(() => {
  const settings = get(accountingSettings);
  const items = [
    {
      label: t('account_settings_display.past_cost_basis'),
      data: settings.calculatePastCostBasis
    },
    {
      label: t('account_settings_display.crypto2crypto'),
      data: settings.includeCrypto2crypto
    },
    {
      label: t('account_settings_display.cost_basis_fees'),
      data: settings.includeFeesInCostBasis || false
    },
    {
      label: t('account_settings_display.gas_costs'),
      data: settings.includeGasCosts
    },
    {
      label: t('account_settings_display.profit_currency'),
      data: settings.profitCurrency || ''
    },
    {
      label: t('account_settings_display.account_asset_movement'),
      data: settings.accountForAssetsMovements
    },
    {
      label: t('account_settings_display.tax_free_period'),
      data: settings.taxfreeAfterPeriod
        ? taxFreePeriod(settings.taxfreeAfterPeriod)
        : false
    }
  ];

  if (settings.ethStakingTaxableAfterWithdrawalEnabled !== undefined) {
    items.push({
      label: t(
        'account_settings_display.eth_staking_taxable_after_withdrawal_enabled'
      ),
      data: !!settings.ethStakingTaxableAfterWithdrawalEnabled
    });
  }

  const costBasis = get(costBasisMethodItem);

  if (costBasis) {
    items.push({
      label: t('account_settings_display.cost_basis_method'),
      data: `${costBasis.identifier.toUpperCase()} (${costBasis.label})`
    });
  }

  return items;
});
</script>

<template>
  <RuiCard>
    <template #header>{{ t('account_settings_display.title') }}</template>
    <template #subheader>
      {{ t('account_settings_display.subtitle') }}
    </template>
    <div class="grid md:grid-cols-2 gap-x-6 gap-y-4 text-body-1">
      <div v-for="item in items" :key="item.label">
        <span class="mr-1 text-rui-text">
          {{ item.label }}
        </span>
        <SuccessDisplay
          v-if="typeof item.data === 'boolean'"
          class="inline -mt-0.5"
          :success="item.data"
        />
        <span v-else class="text-rui-text-secondary">{{ item.data }}</span>
      </div>
    </div>
  </RuiCard>
</template>
