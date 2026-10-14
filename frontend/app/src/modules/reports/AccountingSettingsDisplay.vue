<script setup lang="ts">
import type { ActionDataEntry } from '@/modules/core/common/action';
import type { BaseAccountingSettings, CostBasisMethod } from '@/modules/settings/types/user-settings';
import { useCostBasisMethod } from '@/modules/reports/use-reports';

const { accountingSettings } = defineProps<{ accountingSettings: BaseAccountingSettings }>();

const { t } = useI18n({ useScope: 'global' });
const { costBasisMethodData } = useCostBasisMethod();

function taxFreePeriod(period: number): string {
  const days = period / 86400;
  return t('account_settings_display.days', { days });
}

const costBasisMethodItem = computed<ActionDataEntry<CostBasisMethod> | null>(() => {
  const method = accountingSettings.costBasisMethod;
  if (!method)
    return null;

  return get(costBasisMethodData).find(item => item.identifier === method) || null;
});

interface Item {
  label: string;
  data: boolean | string;
}

const items = computed<Item[]>(() => {
  const settings = accountingSettings;
  const items: Item[] = [
    {
      data: settings.profitCurrency || '',
      label: t('account_settings_display.profit_currency'),
    },
  ];

  const costBasis = get(costBasisMethodItem);
  if (costBasis) {
    items.push({
      data: `${costBasis.identifier.toUpperCase()} (${costBasis.label})`,
      label: t('account_settings_display.cost_basis_method'),
    });
  }

  items.push(
    {
      data: settings.taxfreeAfterPeriod ? taxFreePeriod(settings.taxfreeAfterPeriod) : false,
      label: t('account_settings_display.tax_free_period'),
    },
    {
      data: settings.calculatePastCostBasis,
      label: t('account_settings_display.past_cost_basis'),
    },
    {
      data: settings.includeCrypto2crypto,
      label: t('account_settings_display.crypto2crypto'),
    },
    {
      data: settings.includeFeesInCostBasis || false,
      label: t('account_settings_display.cost_basis_fees'),
    },
    {
      data: settings.includeGasCosts,
      label: t('account_settings_display.gas_costs'),
    },
  );

  if (settings.ethStakingTaxableAfterWithdrawalEnabled !== undefined) {
    items.push({
      data: !!settings.ethStakingTaxableAfterWithdrawalEnabled,
      label: t('account_settings_display.eth_staking_taxable_after_withdrawal_enabled'),
    });
  }

  return items;
});
</script>

<template>
  <section
    class="@container flex flex-col gap-3"
    data-testid="report-accounting-settings-display"
  >
    <div class="flex flex-col gap-0.5">
      <h2 class="text-base font-semibold text-rui-text">
        {{ t('account_settings_display.title') }}
      </h2>
      <p class="text-sm text-rui-text-secondary">
        {{ t('account_settings_display.subtitle') }}
      </p>
    </div>
    <dl class="grid grid-cols-2 @3xl:grid-cols-4 gap-x-6 gap-y-4 p-4 rounded-rui-card border border-rui-divider bg-rui-surface">
      <div
        v-for="item in items"
        :key="item.label"
        class="flex flex-col gap-1 min-w-0"
      >
        <dt class="text-xs text-rui-text-secondary">
          {{ item.label }}
        </dt>
        <dd
          v-if="typeof item.data === 'boolean'"
          class="flex items-center gap-1.5 text-sm text-rui-text"
        >
          <RuiIcon
            :name="item.data ? 'lu-circle-check' : 'lu-circle-minus'"
            :color="item.data ? 'success' : undefined"
            :class="{ 'text-rui-text-secondary': !item.data }"
            size="16"
          />
          {{ item.data ? t('account_settings_display.yes') : t('account_settings_display.no') }}
        </dd>
        <dd
          v-else
          class="text-sm text-rui-text truncate"
          :title="item.data"
        >
          {{ item.data }}
        </dd>
      </div>
    </dl>
  </section>
</template>
