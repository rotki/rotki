<script setup lang="ts">
import type { ProfitLossOverviewItem, Report } from '@/modules/reports/report-types';
import { pluralizeLastWord, toCapitalCase } from '@rotki/common';
import { FiatDisplay } from '@/modules/assets/amount-display/components';
import { calculateTotalProfitLoss } from '@/modules/reports/report-utils';

const {
  flat = false,
  loading = false,
  report,
} = defineProps<{
  report: Report;
  loading?: boolean;
  /** Only the table, for a place that already says what it is, such as a report's expanded row. */
  flat?: boolean;
}>();

const total = computed<ProfitLossOverviewItem>(() => calculateTotalProfitLoss(report));

const { t } = useI18n({ useScope: 'global' });
</script>

<template>
  <section class="flex flex-col gap-3">
    <h2
      v-if="!flat"
      class="text-base font-semibold text-rui-text"
    >
      {{ t('profit_loss_overview.title') }}
    </h2>
    <div class="rounded-rui-card border border-rui-divider bg-rui-surface overflow-clip w-full">
      <table class="w-full text-sm">
        <thead class="text-rui-text-secondary text-xs font-medium border-b border-rui-divider">
          <tr>
            <th class="text-left font-medium px-4 py-3">
              {{ t('common.type') }}
            </th>
            <th class="text-right font-medium px-4 py-3">
              {{ t('profit_loss_overview.headers.tax_free_profit_loss') }}
            </th>
            <th class="text-right font-medium px-4 py-3">
              {{ t('profit_loss_overview.headers.taxable_profit_loss') }}
            </th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="(item, key) in report.overview"
            :key="key"
            class="border-b border-rui-divider"
          >
            <td class="px-4 py-3">
              {{ pluralizeLastWord(toCapitalCase(key)) }}
            </td>
            <td class="text-right px-4 py-3">
              <FiatDisplay
                :value="item.free"
                :currency="report.settings.profitCurrency ?? undefined"
                :loading="loading"
                pnl
              />
            </td>
            <td class="text-right px-4 py-3">
              <FiatDisplay
                :value="item.taxable"
                :currency="report.settings.profitCurrency ?? undefined"
                :loading="loading"
                pnl
              />
            </td>
          </tr>
          <tr
            v-if="Object.keys(report.overview).length === 0"
            class="border-b border-rui-divider"
          >
            <td
              colspan="3"
              class="px-4 py-3 text-rui-text-secondary"
              data-testid="overview-empty"
            >
              {{ t('profit_loss_overview.empty') }}
            </td>
          </tr>
          <tr
            class="font-semibold bg-rui-grey-50 dark:bg-rui-grey-900"
            data-testid="overview-total"
          >
            <td class="px-4 py-3">
              {{ t('common.total') }}
            </td>
            <td class="text-right px-4 py-3">
              <FiatDisplay
                :value="total.free"
                :currency="report.settings.profitCurrency ?? undefined"
                :loading="loading"
                pnl
              />
            </td>
            <td class="text-right px-4 py-3">
              <FiatDisplay
                :value="total.taxable"
                :currency="report.settings.profitCurrency ?? undefined"
                :loading="loading"
                pnl
              />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>
