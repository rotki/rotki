<script setup lang="ts">
import {
  type ProfitLossOverviewItem,
  type SelectedReport
} from '@/types/reports';
import { pluralizeLastWord, toCapitalCase } from '@/utils/text';

const props = withDefaults(
  defineProps<{
    report: SelectedReport;
    symbol?: string | null;
    flat?: boolean;
    loading?: boolean;
  }>(),
  {
    symbol: null,
    flat: false,
    loading: false
  }
);

const { report } = toRefs(props);

const total = computed<ProfitLossOverviewItem>(() =>
  calculateTotalProfitLoss(get(report))
);

const { t } = useI18n();
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('profit_loss_overview.title') }}
    </template>
    <div
      class="!rounded-md border border-rui-grey-300 dark:border-rui-grey-600 w-full"
    >
      <table class="w-full">
        <thead
          class="text-rui-text-secondary font-medium border-b border-default text-xs"
        >
          <tr>
            <th class="text-left pa-4">
              {{ t('common.type') }}
            </th>
            <th class="text-right pa-4">
              {{ t('profit_loss_overview.headers.tax_free_profit_loss') }}
            </th>
            <th class="text-right pa-4">
              {{ t('profit_loss_overview.headers.taxable_profit_loss') }}
            </th>
          </tr>
        </thead>
        <tbody class="text-body-2">
          <tr
            v-for="(item, key) in report.overview"
            :key="key"
            class="border-default border-b"
          >
            <td class="pa-4">{{ pluralizeLastWord(toCapitalCase(key)) }}</td>
            <td class="text-right pa-4">
              <AmountDisplay
                pnl
                force-currency
                :value="item.free"
                :loading="loading"
                :fiat-currency="report.settings.profitCurrency"
              />
            </td>
            <td class="text-right pa-4">
              <AmountDisplay
                pnl
                force-currency
                :value="item.taxable"
                :loading="loading"
                :fiat-currency="report.settings.profitCurrency"
              />
            </td>
          </tr>
          <tr v-if="Object.keys(report.overview).length === 0">
            <td colspan="3" class="pa-4 h-[3rem]" />
          </tr>
          <tr class="border-t border-default text-xs font-medium">
            <td class="pa-4">
              {{ t('common.total') }}
            </td>
            <td class="text-right pa-4">
              <AmountDisplay
                pnl
                force-currency
                :value="total.free"
                :loading="loading"
                :fiat-currency="report.settings.profitCurrency"
              />
            </td>
            <td class="text-right pa-4">
              <AmountDisplay
                pnl
                force-currency
                :value="total.taxable"
                :loading="loading"
                :fiat-currency="report.settings.profitCurrency"
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </RuiCard>
</template>
