<template>
  <card outlined-body :flat="flat">
    <template #title>
      {{ $t('profit_loss_overview.title') }}
    </template>
    <v-simple-table>
      <thead>
        <tr>
          <th
            class="text-left"
            v-text="$t('profit_loss_overview.columns.type')"
          />
          <th
            class="text-right"
            v-text="$t('profit_loss_overview.columns.tax_free_profit_loss')"
          />
          <th
            class="text-right"
            v-text="$t('profit_loss_overview.columns.taxable_profit_loss')"
          />
        </tr>
      </thead>
      <tbody>
        <tr v-for="(item, key) in report.overview" :key="key">
          <td>{{ pluralizeLastWord(toCapitalCase(key)) }}</td>
          <td class="text-right">
            <amount-display
              pnl
              force-currency
              :value="item.free"
              :loading="loading"
              :fiat-currency="report.settings.profitCurrency"
            />
          </td>
          <td class="text-right">
            <amount-display
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
            {{ $t('profit_loss_overview.rows.total') }}
          </td>
          <td class="text-right font-weight-medium text-subtitle-1">
            <amount-display
              pnl
              force-currency
              :value="total.free"
              :loading="loading"
              :fiat-currency="report.settings.profitCurrency"
            />
          </td>
          <td class="text-right font-weight-medium text-subtitle-1">
            <amount-display
              pnl
              force-currency
              :value="total.taxable"
              :loading="loading"
              :fiat-currency="report.settings.profitCurrency"
            />
          </td>
        </tr>
      </tbody>
    </v-simple-table>
  </card>
</template>

<script lang="ts">
import {
  computed,
  defineComponent,
  PropType,
  toRefs
} from '@vue/composition-api';
import { get } from '@vueuse/core';
import AmountDisplay from '@/components/display/AmountDisplay.vue';
import { ProfitLossOverviewItem, Report } from '@/types/reports';
import { calculateTotalProfitLoss } from '@/utils/report';
import { pluralizeLastWord, toCapitalCase } from '@/utils/text';

export default defineComponent({
  name: 'ProfitLossOverview',
  components: {
    AmountDisplay
  },
  props: {
    report: {
      required: true,
      type: Object as PropType<Report>
    },
    symbol: {
      required: true,
      type: String
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
  },
  setup(props) {
    const { report } = toRefs(props);

    const total = computed<ProfitLossOverviewItem>(() => {
      return calculateTotalProfitLoss(get(report));
    });

    return {
      total,
      toCapitalCase,
      pluralizeLastWord
    };
  }
});
</script>
