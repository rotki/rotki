<script setup lang="ts">
import { type PropType } from 'vue';
import {
  type ProfitLossOverviewItem,
  type SelectedReport
} from '@/types/reports';
import { pluralizeLastWord, toCapitalCase } from '@/utils/text';

const props = defineProps({
  report: {
    required: true,
    type: Object as PropType<SelectedReport>
  },
  symbol: {
    required: false,
    type: String as PropType<string | null>,
    default: null
  },
  flat: {
    required: false,
    type: Boolean,
    default: false
  },
  loading: {
    required: false,
    type: Boolean,
    default: false
  }
});

const { report } = toRefs(props);

const total = computed<ProfitLossOverviewItem>(() =>
  calculateTotalProfitLoss(get(report))
);

const { t } = useI18n();
</script>

<template>
  <Card outlined-body :flat="flat">
    <template #title>
      {{ t('profit_loss_overview.title') }}
    </template>
    <VSimpleTable>
      <thead>
        <tr>
          <th class="text-left" v-text="t('common.type')" />
          <th
            class="text-right"
            v-text="t('profit_loss_overview.headers.tax_free_profit_loss')"
          />
          <th
            class="text-right"
            v-text="t('profit_loss_overview.headers.taxable_profit_loss')"
          />
        </tr>
      </thead>
      <tbody>
        <tr v-for="(item, key) in report.overview" :key="key">
          <td>{{ pluralizeLastWord(toCapitalCase(key)) }}</td>
          <td class="text-right">
            <AmountDisplay
              pnl
              force-currency
              :value="item.free"
              :loading="loading"
              :fiat-currency="report.settings.profitCurrency"
            />
          </td>
          <td class="text-right">
            <AmountDisplay
              pnl
              force-currency
              :value="item.taxable"
              :loading="loading"
              :fiat-currency="report.settings.profitCurrency"
            />
          </td>
        </tr>
        <tr>
          <td colspan="3" />
        </tr>
        <tr>
          <td class="font-weight-medium text-subtitle-1">
            {{ t('common.total') }}
          </td>
          <td class="text-right font-weight-medium text-subtitle-1">
            <AmountDisplay
              pnl
              force-currency
              :value="total.free"
              :loading="loading"
              :fiat-currency="report.settings.profitCurrency"
            />
          </td>
          <td class="text-right font-weight-medium text-subtitle-1">
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
    </VSimpleTable>
  </Card>
</template>
