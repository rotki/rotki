<script setup lang="ts">
import type { ProfitLossOverviewItem, Report, SelectedReport } from '@/types/reports';
import AmountDisplay from '@/components/display/amount/AmountDisplay.vue';
import { calculateTotalProfitLoss } from '@/utils/report';

const props = withDefaults(
  defineProps<{
    report: SelectedReport | Report;
    symbol?: string | null;
    flat?: boolean;
    loading?: boolean;
  }>(),
  {
    flat: false,
    loading: false,
    symbol: null,
  },
);

const { report } = toRefs(props);

const total = computed<ProfitLossOverviewItem>(() => calculateTotalProfitLoss(get(report)));

const { t } = useI18n();
</script>

<template>
  <RuiCard>
    <template #header>
      {{ t('profit_loss_overview.title') }}
    </template>
    <div class="!rounded-md border border-rui-grey-300 dark:border-rui-grey-800 w-full">
      <table class="w-full">
        <thead class="text-rui-text-secondary font-medium border-b border-default text-xs">
          <tr>
            <th class="text-left p-4">
              {{ t('common.type') }}
            </th>
            <th class="text-right p-4">
              {{ t('profit_loss_overview.headers.tax_free_profit_loss') }}
            </th>
            <th class="text-right p-4">
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
            <td class="p-4">
              {{ pluralizeLastWord(toCapitalCase(key)) }}
            </td>
            <td class="text-right p-4">
              <AmountDisplay
                pnl
                force-currency
                show-currency="symbol"
                :value="item.free"
                :loading="loading"
                :fiat-currency="report.settings.profitCurrency"
              />
            </td>
            <td class="text-right p-4">
              <AmountDisplay
                pnl
                force-currency
                show-currency="symbol"
                :value="item.taxable"
                :loading="loading"
                :fiat-currency="report.settings.profitCurrency"
              />
            </td>
          </tr>
          <tr v-if="Object.keys(report.overview).length === 0">
            <td
              colspan="3"
              class="p-4 h-[3rem]"
            />
          </tr>
          <tr class="border-t border-default font-medium">
            <td class="p-4">
              {{ t('common.total') }}
            </td>
            <td class="text-right p-4">
              <AmountDisplay
                pnl
                force-currency
                show-currency="symbol"
                :value="total.free"
                :loading="loading"
                :fiat-currency="report.settings.profitCurrency"
              />
            </td>
            <td class="text-right p-4">
              <AmountDisplay
                pnl
                force-currency
                show-currency="symbol"
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
