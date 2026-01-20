<script setup lang="ts">
import type { ProfitLossOverviewItem, Report } from '@/types/reports';
import { pluralizeLastWord, toCapitalCase } from '@rotki/common';
import { FiatDisplay } from '@/modules/amount-display/components';
import { calculateTotalProfitLoss } from '@/utils/report';

const props = withDefaults(
  defineProps<{
    report: Report;
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

const { t } = useI18n({ useScope: 'global' });
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
              <FiatDisplay
                :value="item.free"
                :currency="report.settings.profitCurrency ?? undefined"
                :loading="loading"
                pnl
              />
            </td>
            <td class="text-right p-4">
              <FiatDisplay
                :value="item.taxable"
                :currency="report.settings.profitCurrency ?? undefined"
                :loading="loading"
                pnl
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
              <FiatDisplay
                :value="total.free"
                :currency="report.settings.profitCurrency ?? undefined"
                :loading="loading"
                pnl
              />
            </td>
            <td class="text-right p-4">
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
  </RuiCard>
</template>
